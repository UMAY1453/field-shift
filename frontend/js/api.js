// Yerel FastAPI sunucusunun temel adresi.
const API_BASE_URL =
    window.FIELD_SHIFT_API_URL ?? "http://127.0.0.1:8000";

/**
 * API hatalarının durum kodu ve uygulama koduyla taşınmasını sağlar.
 */
export class ApiError extends Error {
    constructor(message, status = 0, code = "UNKNOWN_ERROR") {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = code;
    }
}

/**
 * Backend hata cevabından kullanıcıya gösterilecek mesajı çıkarır.
 */
function extractErrorMessage(payload, fallbackMessage) {
    const detail = payload?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (detail && typeof detail.message === "string") {
        return detail.message;
    }

    // FastAPI doğrulama hatalarını okunabilir bir metne dönüştürür.
    if (Array.isArray(detail)) {
        return detail
            .map((item) => item?.msg)
            .filter(Boolean)
            .join(" ");
    }

    return fallbackMessage;
}

/**
 * Tüm HTTP isteklerinin ortak hata ve zaman aşımı yönetimini yapar.
 */
async function request(
    path,
    {
        method = "GET",
        body,
        timeout = 10000,
    } = {},
) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeout);

    const options = {
        method,
        signal: controller.signal,
        headers: {
            Accept: "application/json",
        },
    };

    if (body !== undefined) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${path}`, options);
        const contentType = response.headers.get("content-type") ?? "";

        const payload = contentType.includes("application/json")
            ? await response.json()
            : null;

        if (!response.ok) {
            const message = extractErrorMessage(
                payload,
                `İstek başarısız oldu. HTTP ${response.status}`,
            );

            const code = payload?.detail?.code ?? "API_ERROR";

            throw new ApiError(message, response.status, code);
        }

        return payload;
    } catch (error) {
        if (error instanceof ApiError) {
            throw error;
        }

        if (error.name === "AbortError") {
            throw new ApiError(
                "İstek zaman aşımına uğradı. Lütfen tekrar deneyin.",
                0,
                "REQUEST_TIMEOUT",
            );
        }

        throw new ApiError(
            "Backend servisine ulaşılamadı. Sunucunun çalıştığını kontrol edin.",
            0,
            "NETWORK_ERROR",
        );
    } finally {
        window.clearTimeout(timeoutId);
    }
}

/**
 * Backend servisinin çalışıp çalışmadığını kontrol eder.
 */
export function checkHealth() {
    return request("/api/health", {
        timeout: 5000,
    });
}

/**
 * Formdaki ürün seçeneklerini backend üzerinden getirir.
 */
export async function fetchCrops() {
    const payload = await request("/api/crops");

    if (!Array.isArray(payload?.crops)) {
        throw new ApiError(
            "Backend geçerli bir ürün listesi döndürmedi.",
            0,
            "INVALID_CROP_RESPONSE",
        );
    }

    return payload.crops;
}

/**
 * Kullanıcının seçimlerini analiz endpoint'ine gönderir.
 */
export function analyzeClimate(requestBody) {
    return request("/api/analyze", {
        method: "POST",
        body: requestBody,

        // NASA isteği birkaç saniye sürebileceği için daha uzun tutulur.
        timeout: 45000,
    });
}