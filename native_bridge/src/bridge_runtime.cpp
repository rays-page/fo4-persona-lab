#include "f4rp/bridge_runtime.h"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <windows.h>
#include <winhttp.h>

#include <algorithm>
#include <charconv>
#include <cctype>
#include <optional>
#include <sstream>
#include <system_error>
#include <string_view>
#include <utility>

namespace {

class WinHttpHandle {
public:
    WinHttpHandle() = default;
    explicit WinHttpHandle(HINTERNET handle) : handle_(handle) {}

    ~WinHttpHandle() { reset(); }

    WinHttpHandle(const WinHttpHandle&) = delete;
    WinHttpHandle& operator=(const WinHttpHandle&) = delete;

    WinHttpHandle(WinHttpHandle&& other) noexcept : handle_(other.release()) {}

    WinHttpHandle& operator=(WinHttpHandle&& other) noexcept {
        if (this != &other) {
            reset(other.release());
        }
        return *this;
    }

    [[nodiscard]] HINTERNET get() const { return handle_; }
    [[nodiscard]] explicit operator bool() const { return handle_ != nullptr; }

    void reset(HINTERNET new_handle = nullptr) {
        if (handle_ != nullptr) {
            WinHttpCloseHandle(handle_);
        }
        handle_ = new_handle;
    }

    [[nodiscard]] HINTERNET release() {
        HINTERNET old = handle_;
        handle_ = nullptr;
        return old;
    }

private:
    HINTERNET handle_ = nullptr;
};

std::wstring Utf8ToWide(std::string_view input) {
    if (input.empty()) {
        return {};
    }

    const int wide_len = MultiByteToWideChar(
        CP_UTF8,
        MB_ERR_INVALID_CHARS,
        input.data(),
        static_cast<int>(input.size()),
        nullptr,
        0);
    if (wide_len <= 0) {
        return {};
    }

    std::wstring out;
    out.resize(static_cast<std::size_t>(wide_len));
    MultiByteToWideChar(
        CP_UTF8,
        MB_ERR_INVALID_CHARS,
        input.data(),
        static_cast<int>(input.size()),
        out.data(),
        wide_len);
    return out;
}

std::string WideToUtf8(std::wstring_view input) {
    if (input.empty()) {
        return {};
    }

    const int utf8_len = WideCharToMultiByte(
        CP_UTF8,
        0,
        input.data(),
        static_cast<int>(input.size()),
        nullptr,
        0,
        nullptr,
        nullptr);
    if (utf8_len <= 0) {
        return {};
    }

    std::string out;
    out.resize(static_cast<std::size_t>(utf8_len));
    WideCharToMultiByte(
        CP_UTF8,
        0,
        input.data(),
        static_cast<int>(input.size()),
        out.data(),
        utf8_len,
        nullptr,
        nullptr);
    return out;
}

std::string FormatWindowsError(DWORD error_code) {
    LPWSTR buffer = nullptr;
    const DWORD chars = FormatMessageW(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
        nullptr,
        error_code,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        reinterpret_cast<LPWSTR>(&buffer),
        0,
        nullptr);

    std::wstring message;
    if (chars != 0 && buffer != nullptr) {
        message.assign(buffer, chars);
        LocalFree(buffer);
    }

    while (!message.empty() && (message.back() == L'\r' || message.back() == L'\n' || message.back() == L' ')) {
        message.pop_back();
    }

    std::ostringstream stream;
    stream << "WinHTTP error " << error_code;
    if (!message.empty()) {
        stream << ": " << WideToUtf8(message);
    }
    return stream.str();
}

void SkipWhitespace(std::string_view json, std::size_t& offset) {
    while (offset < json.size() && std::isspace(static_cast<unsigned char>(json[offset])) != 0) {
        ++offset;
    }
}

std::optional<std::size_t> FindValueOffset(std::string_view json, std::string_view key) {
    const std::string needle = std::string{"\""} + std::string{key} + "\"";
    const std::size_t key_pos = json.find(needle);
    if (key_pos == std::string_view::npos) {
        return std::nullopt;
    }

    std::size_t value_pos = json.find(':', key_pos + needle.size());
    if (value_pos == std::string_view::npos) {
        return std::nullopt;
    }
    ++value_pos;
    SkipWhitespace(json, value_pos);
    if (value_pos >= json.size()) {
        return std::nullopt;
    }
    return value_pos;
}

void AppendUtf8CodePoint(std::string& out, std::uint32_t code_point) {
    if (code_point <= 0x7F) {
        out.push_back(static_cast<char>(code_point));
        return;
    }

    if (code_point <= 0x7FF) {
        out.push_back(static_cast<char>(0xC0 | ((code_point >> 6) & 0x1F)));
        out.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
        return;
    }

    if (code_point <= 0xFFFF) {
        out.push_back(static_cast<char>(0xE0 | ((code_point >> 12) & 0x0F)));
        out.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
        return;
    }

    if (code_point <= 0x10FFFF) {
        out.push_back(static_cast<char>(0xF0 | ((code_point >> 18) & 0x07)));
        out.push_back(static_cast<char>(0x80 | ((code_point >> 12) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
        return;
    }

    out.push_back('?');
}

std::optional<std::uint32_t> ParseHexCodeUnit(std::string_view json, std::size_t& offset) {
    if (offset + 4 > json.size()) {
        return std::nullopt;
    }

    unsigned int code_unit = 0;
    const auto* start = json.data() + offset;
    const auto* end = start + 4;
    const auto parsed = std::from_chars(start, end, code_unit, 16);
    if (parsed.ec != std::errc{} || parsed.ptr != end) {
        return std::nullopt;
    }

    offset += 4;
    return static_cast<std::uint32_t>(code_unit);
}

std::optional<std::uint32_t> ParseEscapedCodePoint(std::string_view json, std::size_t& offset) {
    const auto first_unit = ParseHexCodeUnit(json, offset);
    if (!first_unit.has_value()) {
        return std::nullopt;
    }

    const std::uint32_t lead = *first_unit;
    if (lead >= 0xD800 && lead <= 0xDBFF) {
        if (offset + 6 > json.size() || json[offset] != '\\' || json[offset + 1] != 'u') {
            return std::nullopt;
        }
        offset += 2;
        const auto second_unit = ParseHexCodeUnit(json, offset);
        if (!second_unit.has_value()) {
            return std::nullopt;
        }
        const std::uint32_t trail = *second_unit;
        if (trail < 0xDC00 || trail > 0xDFFF) {
            return std::nullopt;
        }
        return 0x10000 + (((lead - 0xD800) << 10) | (trail - 0xDC00));
    }

    if (lead >= 0xDC00 && lead <= 0xDFFF) {
        return std::nullopt;
    }

    return lead;
}

std::optional<std::pair<std::string, std::size_t>> ParseJsonStringWithEnd(std::string_view json, std::size_t offset) {
    if (offset >= json.size() || json[offset] != '"') {
        return std::nullopt;
    }

    ++offset;
    std::string out;
    out.reserve(64);

    while (offset < json.size()) {
        const char ch = json[offset++];
        if (ch == '"') {
            return std::pair<std::string, std::size_t>{std::move(out), offset};
        }

        if (ch != '\\') {
            out.push_back(ch);
            continue;
        }

        if (offset >= json.size()) {
            return std::nullopt;
        }

        const char escaped = json[offset++];
        switch (escaped) {
        case '"':
            out.push_back('"');
            break;
        case '\\':
            out.push_back('\\');
            break;
        case '/':
            out.push_back('/');
            break;
        case 'b':
            out.push_back('\b');
            break;
        case 'f':
            out.push_back('\f');
            break;
        case 'n':
            out.push_back('\n');
            break;
        case 'r':
            out.push_back('\r');
            break;
        case 't':
            out.push_back('\t');
            break;
        case 'u': {
            const auto code_point = ParseEscapedCodePoint(json, offset);
            if (!code_point.has_value()) {
                return std::nullopt;
            }
            AppendUtf8CodePoint(out, *code_point);
            break;
        }
        default:
            return std::nullopt;
        }
    }

    return std::nullopt;
}

std::optional<std::string> ParseJsonString(std::string_view json, std::size_t offset) {
    const auto parsed = ParseJsonStringWithEnd(json, offset);
    if (!parsed.has_value()) {
        return std::nullopt;
    }
    return parsed->first;
}

std::optional<bool> ParseJsonBool(std::string_view json, std::size_t offset) {
    if (json.substr(offset, 4) == "true") {
        return true;
    }
    if (json.substr(offset, 5) == "false") {
        return false;
    }
    return std::nullopt;
}

std::optional<std::string> FindJsonString(std::string_view json, std::string_view key) {
    const auto value_offset = FindValueOffset(json, key);
    if (!value_offset.has_value()) {
        return std::nullopt;
    }
    return ParseJsonString(json, *value_offset);
}

std::optional<bool> FindJsonBool(std::string_view json, std::string_view key) {
    const auto value_offset = FindValueOffset(json, key);
    if (!value_offset.has_value()) {
        return std::nullopt;
    }
    return ParseJsonBool(json, *value_offset);
}

std::vector<std::string> FindJsonStringArray(std::string_view json, std::string_view key) {
    const auto value_offset = FindValueOffset(json, key);
    if (!value_offset.has_value()) {
        return {};
    }

    std::size_t cursor = *value_offset;
    if (cursor >= json.size() || json[cursor] != '[') {
        return {};
    }

    ++cursor;
    SkipWhitespace(json, cursor);

    std::vector<std::string> values;
    while (cursor < json.size()) {
        if (json[cursor] == ']') {
            return values;
        }

        const auto value = ParseJsonStringWithEnd(json, cursor);
        if (!value.has_value()) {
            return {};
        }
        values.push_back(value->first);

        cursor = value->second;
        SkipWhitespace(json, cursor);
        if (cursor >= json.size()) {
            return {};
        }

        if (json[cursor] == ',') {
            ++cursor;
            SkipWhitespace(json, cursor);
            continue;
        }

        if (json[cursor] == ']') {
            return values;
        }

        return {};
    }

    return {};
}

std::string JoinStrings(const std::vector<std::string>& parts, std::string_view delimiter) {
    if (parts.empty()) {
        return {};
    }

    std::string out;
    std::size_t total_size = 0;
    for (const auto& part : parts) {
        total_size += part.size();
    }
    total_size += delimiter.size() * (parts.size() - 1);
    out.reserve(total_size);

    for (std::size_t i = 0; i < parts.size(); ++i) {
        if (i != 0) {
            out.append(delimiter);
        }
        out.append(parts[i]);
    }

    return out;
}

std::string EscapeJsonString(std::string_view input) {
    std::string out;
    out.reserve(input.size() + 16);

    for (const char ch : input) {
        switch (ch) {
        case '\\':
            out += "\\\\";
            break;
        case '"':
            out += "\\\"";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            if (static_cast<unsigned char>(ch) < 0x20) {
                out += ' ';
            } else {
                out += ch;
            }
            break;
        }
    }

    return out;
}

std::string BuildRequestBody(const f4rp::ChatRequest& request) {
    std::ostringstream body;
    body << "{";
    body << "\"request_id\":" << request.request_id << ",";
    body << "\"persona_id\":\"" << EscapeJsonString(request.persona_id) << "\",";
    body << "\"session_id\":\"" << EscapeJsonString(request.session_id) << "\",";
    body << "\"message\":\"" << EscapeJsonString(request.player_text) << "\",";
    body << "\"player_name\":\"" << EscapeJsonString(request.player_name) << "\",";
    body << "\"location\":\"" << EscapeJsonString(request.location) << "\",";
    body << "\"speak\":" << (request.speak ? "true" : "false");
    body << "}";
    return body.str();
}

struct HttpResponse {
    int status_code = 0;
    std::string body;
    std::string transport_error;
};

bool EraseFirst(std::deque<std::int32_t>& queue, std::int32_t value) {
    const auto it = std::find(queue.begin(), queue.end(), value);
    if (it == queue.end()) {
        return false;
    }
    queue.erase(it);
    return true;
}

}  // namespace

namespace f4rp {

class BridgeRuntime::HttpClient {
public:
    explicit HttpClient(const BridgeConfig& config) : config_(config) {}

    HttpResponse PostBridgeChat(const ChatRequest& request) {
        if (!EnsureConnected()) {
            return {0, {}, "Failed to initialize WinHTTP handles."};
        }

        const std::wstring endpoint = Utf8ToWide(config_.endpoint);
        if (endpoint.empty()) {
            return {0, {}, "Invalid endpoint path for WinHTTP."};
        }

        WinHttpHandle http_request{WinHttpOpenRequest(
            connection_.get(),
            L"POST",
            endpoint.c_str(),
            nullptr,
            WINHTTP_NO_REFERER,
            WINHTTP_DEFAULT_ACCEPT_TYPES,
            0)};
        if (!http_request) {
            return {0, {}, FormatWindowsError(GetLastError())};
        }

        const std::string request_body = BuildRequestBody(request);
        const DWORD body_size = static_cast<DWORD>(request_body.size());
        const wchar_t* content_type = L"Content-Type: application/json\r\n";

        if (!WinHttpSendRequest(
                http_request.get(),
                content_type,
                -1L,
                request_body.empty() ? WINHTTP_NO_REQUEST_DATA : static_cast<LPVOID>(const_cast<char*>(request_body.data())),
                body_size,
                body_size,
                0)) {
            return {0, {}, FormatWindowsError(GetLastError())};
        }

        if (!WinHttpReceiveResponse(http_request.get(), nullptr)) {
            return {0, {}, FormatWindowsError(GetLastError())};
        }

        DWORD status_code = 0;
        DWORD status_code_size = sizeof(status_code);
        if (!WinHttpQueryHeaders(
                http_request.get(),
                WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                WINHTTP_HEADER_NAME_BY_INDEX,
                &status_code,
                &status_code_size,
                WINHTTP_NO_HEADER_INDEX)) {
            return {0, {}, FormatWindowsError(GetLastError())};
        }

        std::string response_body;
        while (true) {
            DWORD available_size = 0;
            if (!WinHttpQueryDataAvailable(http_request.get(), &available_size)) {
                return {static_cast<int>(status_code), {}, FormatWindowsError(GetLastError())};
            }

            if (available_size == 0) {
                break;
            }

            std::string chunk;
            chunk.resize(available_size);

            DWORD downloaded_size = 0;
            if (!WinHttpReadData(http_request.get(), chunk.data(), available_size, &downloaded_size)) {
                return {static_cast<int>(status_code), {}, FormatWindowsError(GetLastError())};
            }

            chunk.resize(downloaded_size);
            response_body.append(chunk);
        }

        return {static_cast<int>(status_code), std::move(response_body), {}};
    }

private:
    bool EnsureConnected() {
        if (session_ && connection_) {
            return true;
        }

        session_.reset(WinHttpOpen(
            L"F4RP-NativeBridge/0.1",
            WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
            WINHTTP_NO_PROXY_NAME,
            WINHTTP_NO_PROXY_BYPASS,
            0));
        if (!session_) {
            session_.reset(WinHttpOpen(
                L"F4RP-NativeBridge/0.1",
                WINHTTP_ACCESS_TYPE_NO_PROXY,
                WINHTTP_NO_PROXY_NAME,
                WINHTTP_NO_PROXY_BYPASS,
                0));
        }
        if (!session_) {
            return false;
        }

        if (!WinHttpSetTimeouts(
                session_.get(),
                static_cast<int>(config_.connect_timeout.count()),
                static_cast<int>(config_.connect_timeout.count()),
                static_cast<int>(config_.send_timeout.count()),
                static_cast<int>(config_.receive_timeout.count()))) {
            session_.reset();
            return false;
        }

        const std::wstring host = Utf8ToWide(config_.host);
        if (host.empty()) {
            session_.reset();
            return false;
        }

        connection_.reset(WinHttpConnect(session_.get(), host.c_str(), config_.port, 0));
        if (!connection_) {
            session_.reset();
            return false;
        }

        return true;
    }

    BridgeConfig config_;
    WinHttpHandle session_;
    WinHttpHandle connection_;
};

BridgeRuntime::BridgeRuntime(BridgeConfig config) : config_(std::move(config)) {
    if (config_.worker_count == 0) {
        config_.worker_count = 1;
    }

    workers_.reserve(config_.worker_count);
    for (std::size_t i = 0; i < config_.worker_count; ++i) {
        workers_.emplace_back([this]() { WorkerLoop(); });
    }
}

BridgeRuntime::~BridgeRuntime() {
    stopping_.store(true);
    requests_cv_.notify_all();

    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
}

bool BridgeRuntime::Enqueue(ChatRequest request) {
    if (request.request_id <= 0 || request.persona_id.empty() || request.player_text.empty()) {
        return false;
    }

    {
        std::lock_guard lock(requests_mutex_);
        if (pending_requests_.size() >= config_.max_pending_requests) {
            return false;
        }
        pending_requests_.push_back(std::move(request));
    }

    requests_cv_.notify_one();
    return true;
}

std::int32_t BridgeRuntime::PopCompletedRequestId() {
    std::lock_guard lock(results_mutex_);
    if (completed_request_ids_.empty()) {
        return -1;
    }

    const std::int32_t request_id = completed_request_ids_.front();
    completed_request_ids_.pop_front();
    return request_id;
}

bool BridgeRuntime::PeekResult(std::int32_t request_id, ChatResult& out_result) const {
    std::lock_guard lock(results_mutex_);
    const auto it = results_.find(request_id);
    if (it == results_.end()) {
        return false;
    }

    out_result = it->second;
    return true;
}

void BridgeRuntime::ReleaseResult(std::int32_t request_id) {
    std::lock_guard lock(results_mutex_);
    results_.erase(request_id);
    EraseFirst(result_eviction_order_, request_id);
}

std::size_t BridgeRuntime::PendingQueueDepth() const {
    std::lock_guard lock(requests_mutex_);
    return pending_requests_.size();
}

void BridgeRuntime::WorkerLoop() {
    HttpClient client(config_);

    while (true) {
        ChatRequest request;

        {
            std::unique_lock lock(requests_mutex_);
            requests_cv_.wait(lock, [this]() { return stopping_.load() || !pending_requests_.empty(); });

            if (stopping_.load() && pending_requests_.empty()) {
                return;
            }

            request = std::move(pending_requests_.front());
            pending_requests_.pop_front();
        }

        ChatResult result = ProcessRequest(client, request);

        {
            std::lock_guard lock(results_mutex_);
            const std::int32_t request_id = result.request_id;

            results_[request_id] = std::move(result);
            completed_request_ids_.push_back(request_id);
            result_eviction_order_.push_back(request_id);

            while (result_eviction_order_.size() > config_.max_completed_results) {
                const std::int32_t stale_request_id = result_eviction_order_.front();
                result_eviction_order_.pop_front();
                results_.erase(stale_request_id);
                EraseFirst(completed_request_ids_, stale_request_id);
            }
        }
    }
}

ChatResult BridgeRuntime::ProcessRequest(HttpClient& client, const ChatRequest& request) const {
    ChatResult result;
    result.request_id = request.request_id;

    const HttpResponse response = client.PostBridgeChat(request);
    if (!response.transport_error.empty()) {
        result.error = response.transport_error;
        return result;
    }

    if (response.status_code < 200 || response.status_code >= 300) {
        result.error = FindJsonString(response.body, "error").value_or("HTTP " + std::to_string(response.status_code));
        return result;
    }

    const std::optional<bool> accepted = FindJsonBool(response.body, "accepted");
    if (accepted.has_value() && !accepted.value()) {
        result.error = FindJsonString(response.body, "error").value_or("Bridge request was rejected.");
        return result;
    }

    result.reply_text = FindJsonString(response.body, "reply").value_or("");
    result.session_id = FindJsonString(response.body, "session_id").value_or("");
    result.audio_file_path = FindJsonString(response.body, "audio_file_path").value_or("");
    if (result.audio_file_path.empty()) {
        result.audio_file_path = FindJsonString(response.body, "audio_url").value_or("");
    }

    const std::vector<std::string> warnings = FindJsonStringArray(response.body, "warnings");
    result.warning = JoinStrings(warnings, "; ");

    if (result.reply_text.empty()) {
        result.error = FindJsonString(response.body, "error").value_or("Response did not include reply text.");
        return result;
    }

    result.success = true;
    return result;
}

}  // namespace f4rp
