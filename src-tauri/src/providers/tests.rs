use super::*;

fn compatible(endpoint: &str) -> ProviderConfig {
    ProviderConfig {
        provider: Provider::Compatible,
        endpoint: Some(endpoint.into()),
        model: "example/model".into(),
    }
}

#[test]
fn only_compatible_provider_accepts_endpoint_overrides() {
    for endpoint in [
        "http://localhost:11434/v1",
        "http://127.0.0.1:1234/v1",
        "http://[::1]:1234/v1",
        "https://example.org/api/v1",
    ] {
        assert!(compatible(endpoint).validate().is_ok(), "{endpoint}");
    }
    for endpoint in [
        "http://example.org/v1",
        "http://localhost.example.org/v1",
        "http://192.168.0.2/v1",
        "https://user:pass@example.org/v1",
        "https://example.org/v1?key=secret",
        "https://example.org/v1#fragment",
        "file:///v1",
    ] {
        assert!(compatible(endpoint).validate().is_err(), "{endpoint}");
    }
    let mut config = compatible("https://example.org/v1");
    config.provider = Provider::OpenAi;
    assert!(config.validate().is_err());
}

#[test]
fn compatible_credentials_are_bound_to_canonical_base_url() {
    let a = compatible("https://Example.ORG:443/api/v1/");
    let b = compatible("https://example.org/api/v1");
    let c = compatible("https://example.org/another/v1");
    assert_eq!(a.credential_scope().unwrap(), b.credential_scope().unwrap());
    assert_ne!(a.credential_scope().unwrap(), c.credential_scope().unwrap());
}

#[test]
fn provider_requests_keep_dictation_separate_from_system_instructions() {
    let client = Client::new();
    for (provider, path, header, body_pointer) in [
        (
            Provider::OpenAi,
            "/v1/responses",
            "authorization",
            "/input/1/content/0/text",
        ),
        (
            Provider::Xai,
            "/v1/responses",
            "authorization",
            "/input/1/content/0/text",
        ),
        (
            Provider::Gemini,
            "/v1beta/models/test:generateContent",
            "x-goog-api-key",
            "/contents/0/parts/0/text",
        ),
        (
            Provider::Anthropic,
            "/v1/messages",
            "x-api-key",
            "/messages/0/content",
        ),
        (
            Provider::OpenRouter,
            "/api/v1/chat/completions",
            "authorization",
            "/messages/1/content",
        ),
    ] {
        let config = ProviderConfig {
            provider,
            endpoint: None,
            model: "test".into(),
        };
        let base = config.base_url().unwrap();
        let request = cleanup_request(
            &client,
            &config,
            &base,
            Some("test-credential"),
            "Edit text.",
            "Grüße\nNeue Zeile",
        )
        .unwrap()
        .build()
        .unwrap();
        assert_eq!(request.url().path(), path);
        assert_eq!(request.url().query(), None);
        assert!(request.headers()[header].is_sensitive());
        let body: Value =
            serde_json::from_slice(request.body().unwrap().as_bytes().unwrap()).unwrap();
        assert_eq!(body.pointer(body_pointer).unwrap(), "Grüße\nNeue Zeile");
        if matches!(provider, Provider::OpenAi | Provider::Xai) {
            assert_eq!(body["store"], false);
        }
    }
}

#[test]
fn native_model_ids_cannot_change_gemini_request_path() {
    let mut config = ProviderConfig {
        provider: Provider::Gemini,
        endpoint: None,
        model: "models/gemini-2.5-flash".into(),
    };
    assert_eq!(config.model_id().unwrap(), "gemini-2.5-flash");
    for bad in [
        "../models",
        "test:embedContent",
        "models/../test",
        "test%2Fother",
    ] {
        config.model = bad.into();
        assert!(config.model_id().is_err(), "{bad}");
    }
}

#[test]
fn extracts_visible_text_without_thoughts_or_partial_answers() {
    for (provider, response) in [
        (
            Provider::OpenAi,
            json!({"status":"completed","output":[{"type":"reasoning","content":[{"type":"reasoning_text","text":"private"}]},{"type":"message","role":"assistant","content":[{"type":"output_text","text":"Grüße\nBerlin"}]}]}),
        ),
        (
            Provider::Gemini,
            json!({"candidates":[{"finishReason":"STOP","content":{"parts":[{"thought":true,"text":"private"},{"text":"Grüße\nBerlin"}]}}]}),
        ),
        (
            Provider::Anthropic,
            json!({"stop_reason":"end_turn","content":[{"type":"thinking","thinking":"private"},{"type":"text","text":"Grüße\nBerlin"}]}),
        ),
        (
            Provider::OpenRouter,
            json!({"choices":[{"finish_reason":"stop","message":{"content":"Grüße\nBerlin","reasoning":"private"}}]}),
        ),
    ] {
        assert_eq!(parse_cleanup(provider, &response).unwrap(), "Grüße\nBerlin");
    }
    assert!(parse_cleanup(
        Provider::OpenAi,
        &json!({"status":"incomplete","output":[]})
    )
    .is_err());
    assert!(parse_cleanup(
        Provider::OpenRouter,
        &json!({"choices":[{"finish_reason":"length","message":{"content":"partial"}}]})
    )
    .is_err());
    assert!(parse_cleanup(
        Provider::Gemini,
        &json!({"candidates":[{"finishReason":"SAFETY"}]})
    )
    .is_err());
}

#[test]
fn model_catalog_uses_provider_capability_metadata() {
    let google = json!({"models":[
        {"name":"models/gemini","supportedGenerationMethods":["generateContent"]},
        {"name":"models/embedder","supportedGenerationMethods":["embedContent"]}
    ]});
    assert_eq!(parse_models(Provider::Gemini, &google).unwrap(), ["gemini"]);
    let router = json!({"data":[
        {"id":"example/text","architecture":{"input_modalities":["text"],"output_modalities":["text"]}},
        {"id":"example/image","architecture":{"input_modalities":["text"],"output_modalities":["image"]}}
    ]});
    assert_eq!(
        parse_models(Provider::OpenRouter, &router).unwrap(),
        ["example/text"]
    );
}

#[test]
fn error_messages_do_not_echo_provider_responses() {
    let billing = status_error(
        429,
        Some(&json!({"error":{"code":"insufficient_quota","message":"sensitive transcript"}})),
    );
    assert!(billing.contains("Kontingent"));
    assert!(!billing.contains("sensitive transcript"));
    let limited = status_error(429, None);
    assert!(limited.contains("zu viele"));
    assert_ne!(billing, limited);
    let rejected = status_error(
        400,
        Some(&json!({"error":{"code":400,"details":[{"reason":"API_KEY_INVALID"}]}})),
    );
    assert!(rejected.contains("API-Schlüssel"));
}

fn mock_response(
    status: &str,
    extra_headers: &str,
    body: &str,
) -> (std::net::SocketAddr, std::thread::JoinHandle<String>) {
    use std::io::{BufRead, BufReader, Read, Write};
    let listener = std::net::TcpListener::bind(("127.0.0.1", 0)).unwrap();
    let address = listener.local_addr().unwrap();
    let response = format!("HTTP/1.1 {status}\r\nConnection: close\r\nContent-Type: application/json\r\nContent-Length: {}\r\n{extra_headers}\r\n{body}", body.len());
    let server = std::thread::spawn(move || {
        let (socket, _) = listener.accept().unwrap();
        socket
            .set_read_timeout(Some(Duration::from_secs(5)))
            .unwrap();
        let mut reader = BufReader::new(socket);
        let mut headers = String::new();
        let mut content_len = 0;
        loop {
            let mut line = String::new();
            assert!(reader.read_line(&mut line).unwrap() > 0);
            if line == "\r\n" {
                break;
            }
            if let Some(value) = line.to_ascii_lowercase().strip_prefix("content-length:") {
                content_len = value.trim().parse().unwrap();
            }
            headers.push_str(&line);
        }
        let mut body = vec![0; content_len];
        reader.read_exact(&mut body).unwrap();
        reader.get_mut().write_all(response.as_bytes()).unwrap();
        headers + &String::from_utf8(body).unwrap()
    });
    (address, server)
}

#[tokio::test]
async fn loopback_cleanup_works_without_key_or_external_network() {
    let (address, server) = mock_response(
        "200 OK",
        "",
        r#"{"choices":[{"finish_reason":"stop","message":{"content":"Guten Morgen!"}}]}"#,
    );
    let config = compatible(&format!("http://{address}/v1"));
    let output = cleanup(&config, "Edit text.", "Guten Morgen")
        .await
        .unwrap();
    assert_eq!(output, "Guten Morgen!");
    let request = server.join().unwrap();
    assert!(request.starts_with("POST /v1/chat/completions "));
    assert!(!request.to_ascii_lowercase().contains("authorization:"));
    assert!(request.contains("Guten Morgen"));
}

#[tokio::test]
async fn redirects_cannot_forward_dictation() {
    let (address, server) = mock_response(
        "307 Temporary Redirect",
        "Location: http://127.0.0.1:1/leak\r\n",
        "{}",
    );
    let config = compatible(&format!("http://{address}/v1"));
    let result = cleanup(&config, "Edit text.", "Privat").await;
    assert!(result.unwrap_err().contains("Weiterleitung"));
    server.join().unwrap();
}

#[tokio::test]
async fn http_rate_limit_is_reported_without_echoing_sensitive_text() {
    let (address, server) = mock_response(
        "429 Too Many Requests",
        "",
        r#"{"error":{"message":"private text"}}"#,
    );
    let config = compatible(&format!("http://{address}/v1"));
    let result = cleanup(&config, "Edit text.", "Private input").await;
    assert_eq!(result.unwrap_err(), status_error(429, None));
    server.join().unwrap();
}

#[tokio::test]
async fn timeout_is_reported_without_retries() {
    let listener = std::net::TcpListener::bind(("127.0.0.1", 0)).unwrap();
    let address = listener.local_addr().unwrap();
    let request = http_client()
        .unwrap()
        .get(format!("http://{address}/v1/models"))
        .timeout(Duration::from_millis(40));
    let result = send_json(request).await;
    assert!(result.unwrap_err().contains("nicht rechtzeitig"));
}
