#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace f4rp {

struct BridgeConfig {
    std::string host = "127.0.0.1";
    std::uint16_t port = 8765;
    std::string endpoint = "/api/bridge/chat";
    std::chrono::milliseconds connect_timeout{1500};
    std::chrono::milliseconds send_timeout{3000};
    std::chrono::milliseconds receive_timeout{15000};
    std::size_t worker_count = 2;
    std::size_t max_pending_requests = 128;
    std::size_t max_completed_results = 512;
};

struct ChatRequest {
    std::int32_t request_id = -1;
    std::string persona_id;
    std::string session_id;
    std::string player_text;
    std::string player_name;
    std::string location;
    bool speak = true;
};

struct ChatResult {
    std::int32_t request_id = -1;
    bool success = false;
    std::string reply_text;
    std::string session_id;
    std::string audio_path;
    std::string warning;
    std::string error;
};

class BridgeRuntime {
public:
    explicit BridgeRuntime(BridgeConfig config = {});
    ~BridgeRuntime();

    BridgeRuntime(const BridgeRuntime&) = delete;
    BridgeRuntime& operator=(const BridgeRuntime&) = delete;

    bool Enqueue(ChatRequest request);

    std::int32_t PopCompletedRequestId();
    bool PeekResult(std::int32_t request_id, ChatResult& out_result) const;
    void ReleaseResult(std::int32_t request_id);

    std::size_t PendingQueueDepth() const;

private:
    class HttpClient;

    void WorkerLoop();
    ChatResult ProcessRequest(HttpClient& client, const ChatRequest& request) const;

    BridgeConfig config_;

    mutable std::mutex requests_mutex_;
    std::condition_variable requests_cv_;
    std::deque<ChatRequest> pending_requests_;

    mutable std::mutex results_mutex_;
    std::unordered_map<std::int32_t, ChatResult> results_;
    std::deque<std::int32_t> completed_request_ids_;
    std::deque<std::int32_t> result_eviction_order_;

    std::atomic<bool> stopping_{false};
    std::vector<std::thread> workers_;
};

}  // namespace f4rp
