import {
    analyzeClimate,
    checkHealth,
    fetchCrops,
} from "./api.js";

import {
    initializeMap,
    invalidateMapSize,
    useCurrentLocation,
} from "./map.js";

import {
    renderClimateChart,
} from "./charts.js";

import {
    clearError,
    populateCrops,
    readAnalysisRequest,
    renderAnalysisResult,
    scrollToForm,
    scrollToResults,
    setApiStatus,
    setDefaultDateRange,
    setLoading,
    showCropsUnavailable,
    showError,
    updateSelectedLocation,
} from "./ui.js";

/**
 * Backend bağlantı durumunu kontrol eder.
 */
async function initializeHealthCheck() {
    setApiStatus("checking");

    try {
        const response = await checkHealth();

        if (response?.status !== "ok") {
            throw new Error("Backend sağlıklı cevap vermedi.");
        }

        setApiStatus("online");
    } catch (error) {
        console.warn("Backend health check başarısız:", error);
        setApiStatus("offline");
    }
}

/**
 * Backend'den ürün listesini getirir.
 */
async function initializeCrops() {
    try {
        const crops = await fetchCrops();
        populateCrops(crops);
    } catch (error) {
        console.error("Ürün listesi alınamadı:", error);
        showCropsUnavailable();
        showError(
            "Ürün listesi alınamadı. Backend servisinin çalıştığını kontrol edin.",
        );
    }
}

/**
 * Harita seçiminden gelen koordinatları forma aktarır.
 */
function handleLocationChange(coordinates) {
    updateSelectedLocation(coordinates);
    clearError();
}

/**
 * Tarayıcının konum özelliğini kullanır.
 */
async function handleCurrentLocation() {
    const button = document.getElementById("use-location-button");
    const originalText = button.textContent;

    button.disabled = true;
    button.textContent = "Konum alınıyor...";

    try {
        clearError();
        await useCurrentLocation();
    } catch (error) {
        showError(error.message);
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}

/**
 * Formu doğrular, backend'e gönderir ve sonucu gösterir.
 */
async function handleAnalysisSubmit(event) {
    event.preventDefault();
    clearError();

    try {
        const requestBody = readAnalysisRequest(event.currentTarget);

        setLoading(true);

        const result = await analyzeClimate(requestBody);

        renderAnalysisResult(result);
        renderClimateChart(result.monthly_climate ?? []);
        scrollToResults();
    } catch (error) {
        console.error("Analiz hatası:", error);
        showError(
            error.message ??
                "Analiz sırasında beklenmeyen bir hata oluştu.",
        );
    } finally {
        setLoading(false);
    }
}

/**
 * Sayfadaki kullanıcı etkileşimlerini ilgili fonksiyonlara bağlar.
 */
function registerEventListeners() {
    document
        .getElementById("analysis-form")
        .addEventListener("submit", handleAnalysisSubmit);

    document
        .getElementById("use-location-button")
        .addEventListener("click", handleCurrentLocation);

    document
        .getElementById("scroll-to-form-button")
        .addEventListener("click", scrollToForm);

    // Ekran boyutu değiştiğinde Leaflet haritasını düzeltir.
    let resizeTimer = null;

    window.addEventListener("resize", () => {
        window.clearTimeout(resizeTimer);

        resizeTimer = window.setTimeout(() => {
            invalidateMapSize();
        }, 150);
    });
}

/**
 * Frontend uygulamasını başlatır.
 */
function initializeApplication() {
    try {
        setDefaultDateRange();
        initializeMap(handleLocationChange);
        registerEventListeners();

        // Birbirinden bağımsız başlangıç istekleri paralel çalışır.
        void initializeHealthCheck();
        void initializeCrops();
    } catch (error) {
        console.error("Uygulama başlatılamadı:", error);
        showError(
            error.message ??
                "Uygulama başlatılırken bir hata oluştu.",
        );
        setApiStatus("offline");
    }
}

window.addEventListener("DOMContentLoaded", initializeApplication);