import Foundation

struct OcrPayload: Encodable {
    let engine: String
    let status: String
    let text: String
    let lines: [String]
    let line_count: Int
    let region_count: Int
    let warning: String
}

func exitCode(for status: String) -> Int32 {
    switch status {
    case "success", "no-text", "unavailable":
        return 0
    case "failed":
        return 1
    default:
        return 1
    }
}

func fallbackJSONString(status: String, warning: String) -> String {
    return "{\"engine\":\"apple-vision\",\"status\":\"\(status)\",\"text\":\"\",\"lines\":[],\"line_count\":0,\"region_count\":0,\"warning\":\"\(warning)\"}"
}

func emit(_ payload: OcrPayload) -> Never {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.withoutEscapingSlashes]

    if let data = try? encoder.encode(payload),
       let output = String(data: data, encoding: .utf8) {
        print(output)
    } else {
        print(fallbackJSONString(status: "failed", warning: "failed to encode JSON"))
        exit(1)
    }

    exit(exitCode(for: payload.status))
}

#if canImport(AppKit) && canImport(Vision)
import AppKit
import Vision

func cgImage(from path: String) -> CGImage? {
    guard let image = NSImage(contentsOfFile: path) else {
        return nil
    }

    var proposedRect = NSRect(origin: .zero, size: image.size)
    return image.cgImage(forProposedRect: &proposedRect, context: nil, hints: nil)
}

let arguments = CommandLine.arguments
guard arguments.count == 2 else {
    emit(
        OcrPayload(
            engine: "apple-vision",
            status: "failed",
            text: "",
            lines: [],
            line_count: 0,
            region_count: 0,
            warning: "usage: swift tools/vision_ocr.swift <image-path>"
        )
    )
}

let imagePath = arguments[1]
guard FileManager.default.fileExists(atPath: imagePath) else {
    emit(
        OcrPayload(
            engine: "apple-vision",
            status: "failed",
            text: "",
            lines: [],
            line_count: 0,
            region_count: 0,
            warning: "image path does not exist"
        )
    )
}

guard let image = cgImage(from: imagePath) else {
    emit(
        OcrPayload(
            engine: "apple-vision",
            status: "failed",
            text: "",
            lines: [],
            line_count: 0,
            region_count: 0,
            warning: "failed to decode image"
        )
    )
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: image, options: [:])

do {
    try handler.perform([request])
} catch {
    emit(
        OcrPayload(
            engine: "apple-vision",
            status: "failed",
            text: "",
            lines: [],
            line_count: 0,
            region_count: 0,
            warning: "Vision request failed: \(error.localizedDescription)"
        )
    )
}

let observations = (request.results as? [VNRecognizedTextObservation]) ?? []
let lines = observations.compactMap { observation in
    observation.topCandidates(1).first?.string.trimmingCharacters(in: .whitespacesAndNewlines)
}.filter { !$0.isEmpty }

let status = lines.isEmpty ? "no-text" : "success"
let warning = lines.isEmpty ? "no text detected" : ""

emit(
    OcrPayload(
        engine: "apple-vision",
        status: status,
        text: lines.joined(separator: "\n"),
        lines: lines,
        line_count: lines.count,
        region_count: observations.count,
        warning: warning
    )
)

#else
emit(
    OcrPayload(
    engine: "apple-vision",
    status: "unavailable",
    text: "",
    lines: [],
    line_count: 0,
    region_count: 0,
    warning: "Vision OCR is unavailable on this platform"
)
)

#endif
