#include "f4rp/bridge_runtime.h"

#include <chrono>
#include <iostream>
#include <string>
#include <thread>

int main(int argc, char** argv) {
    f4rp::BridgeConfig config;
    if (argc > 1) {
        config.host = argv[1];
    }
    if (argc > 2) {
        config.port = static_cast<std::uint16_t>(std::stoi(argv[2]));
    }

    f4rp::BridgeRuntime runtime(config);

    f4rp::ChatRequest request;
    request.request_id = 1;
    request.persona_id = "steve-jobs";
    request.session_id = "";
    request.player_text = "Give me one design principle for a Pip-Boy app.";
    request.player_name = "Sole Survivor";
    request.location = "Diamond City";
    request.speak = false;

    if (!runtime.Enqueue(request)) {
        std::cerr << "Failed to enqueue request.\n";
        return 1;
    }

    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(20);
    while (std::chrono::steady_clock::now() < deadline) {
        const std::int32_t request_id = runtime.PopCompletedRequestId();
        if (request_id > 0) {
            f4rp::ChatResult result;
            if (!runtime.PeekResult(request_id, result)) {
                std::cerr << "Result vanished before read.\n";
                return 2;
            }

            if (result.success) {
                std::cout << "Reply: " << result.reply_text << "\n";
                if (!result.session_id.empty()) {
                    std::cout << "Session: " << result.session_id << "\n";
                }
                if (!result.audio_path.empty()) {
                    std::cout << "Audio: " << result.audio_path << "\n";
                }
                if (!result.warning.empty()) {
                    std::cout << "Warning: " << result.warning << "\n";
                }
            } else {
                std::cerr << "Error: " << result.error << "\n";
                runtime.ReleaseResult(request_id);
                return 3;
            }

            runtime.ReleaseResult(request_id);
            return 0;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    std::cerr << "Timed out waiting for response.\n";
    return 4;
}
