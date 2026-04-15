/*
 * F4SE/CommonLibF4 adapter template for f4rp::BridgeRuntime.
 *
 * This file is intentionally not part of the default CMake target in this repo,
 * because the F4SE SDK/CommonLibF4 toolchain is not vendored here.
 *
 * Copy this into your SDK-backed plugin project and replace TODO sections with
 * concrete registration calls for your chosen runtime (raw F4SE or CommonLibF4).
 */

#include "f4rp/bridge_runtime.h"

#if 0
#include <F4SE/F4SE.h>
#include <RE/Bethesda/BSScript/IVirtualMachine.h>

namespace {

f4rp::BridgeRuntime& Runtime() {
    static f4rp::BridgeRuntime runtime{};
    return runtime;
}

bool SubmitChat(
    std::int32_t request_id,
    std::string persona_id,
    std::string session_id,
    std::string player_text,
    std::string player_name,
    std::string location,
    bool speak) {
    f4rp::ChatRequest request;
    request.request_id = request_id;
    request.persona_id = std::move(persona_id);
    request.session_id = std::move(session_id);
    request.player_text = std::move(player_text);
    request.player_name = std::move(player_name);
    request.location = std::move(location);
    request.speak = speak;
    return Runtime().Enqueue(std::move(request));
}

std::int32_t PopCompletedRequestId() {
    return Runtime().PopCompletedRequestId();
}

bool WasRequestSuccessful(std::int32_t request_id) {
    f4rp::ChatResult result;
    return Runtime().PeekResult(request_id, result) && result.success;
}

std::string GetReplyText(std::int32_t request_id) {
    f4rp::ChatResult result;
    return Runtime().PeekResult(request_id, result) ? result.reply_text : "";
}

std::string GetSessionId(std::int32_t request_id) {
    f4rp::ChatResult result;
    return Runtime().PeekResult(request_id, result) ? result.session_id : "";
}

std::string GetAudioPath(std::int32_t request_id) {
    f4rp::ChatResult result;
    return Runtime().PeekResult(request_id, result) ? result.audio_path : "";
}

std::string GetWarning(std::int32_t request_id) {
    f4rp::ChatResult result;
    return Runtime().PeekResult(request_id, result) ? result.warning : "";
}

std::string GetError(std::int32_t request_id) {
    f4rp::ChatResult result;
    return Runtime().PeekResult(request_id, result) ? result.error : "";
}

void ReleaseResult(std::int32_t request_id) {
    Runtime().ReleaseResult(request_id);
}

std::int32_t GetQueueDepth() {
    return static_cast<std::int32_t>(Runtime().PendingQueueDepth());
}

bool BindPapyrus(RE::BSScript::IVirtualMachine* vm) {
    // TODO: Register all functions above under script class name "F4RP_NativeBridge".
    // Suggested names should match the Papyrus declarations exactly:
    // - SubmitChat
    // - PopCompletedRequestId
    // - WasRequestSuccessful
    // - GetReplyText
    // - GetSessionId
    // - GetAudioPath
    // - GetWarning
    // - GetError
    // - ReleaseResult
    // - GetQueueDepth
    return vm != nullptr;
}

}  // namespace

extern "C" DLLEXPORT constinit auto F4SEPlugin_Version = [] {
    F4SE::PluginVersionData version{};
    version.PluginVersion(1);
    version.PluginName("F4RPNativeBridge");
    version.AuthorName("fo4_persona_lab");
    version.UsesAddressLibrary(true);
    version.CompatibleVersions({F4SE::RUNTIME_LATEST});
    return version;
}();

extern "C" DLLEXPORT bool F4SEAPI F4SEPlugin_Load(const F4SE::LoadInterface* f4se) {
    F4SE::Init(f4se);

    const auto* papyrus = F4SE::GetPapyrusInterface();
    if (!papyrus) {
        return false;
    }

    papyrus->Register(BindPapyrus);
    return true;
}
#endif
