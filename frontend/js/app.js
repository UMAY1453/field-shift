import {
    analyzeClimate,
    checkHealth,
    fetchCrops,
} from "./api.js";

import {
    initializeMap,
    invalidateMapSize,
    resetMapSelection,
    setMapLocation,
    useCurrentLocation,
} from "./map.js";

import {
    clearClimateChart,
    renderClimateChart,
} from "./charts.js";

import {
    clearError,
    populateCrops,
    readAnalysisRequest,
    resetAnalysisForm,
    renderAnalysisResult,
    scrollToForm,
    scrollToResults,
    setLoading,
    showCropsUnavailable,
    showError,
    updateSelectedLocation,
} from "./ui.js";

/**
 * Backend bağlantısını kullanıcıya teknik durum göstermeden kontrol eder.
 */
async function initializeHealthCheck() {
    try {
        const response = await checkHealth();

        if (response?.status !== "ok") {
            throw new Error("Backend sağlıklı cevap vermedi.");
        }
    } catch (error) {
        console.warn(
            "Backend health check başarısız:",
            error,
        );
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
 * Elle girilen koordinatları doğrular ve haritadaki konumu günceller.
 */
function handleManualCoordinates() {
    const latitudeInput = document.getElementById("latitude");
    const longitudeInput = document.getElementById("longitude");

    const latitudeValue = latitudeInput.value;
    const longitudeValue = longitudeInput.value;

    // İki alan da doldurulmadan harita güncellenmez.
    if (!latitudeValue || !longitudeValue) {
        return;
    }

    try {
        setMapLocation(latitudeValue, longitudeValue);
        clearError();
    } catch (error) {
        showError(error.message);
    }
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
 * Eski analiz verilerini temizleyerek yeni analiz formunu hazırlar.
 */
function handleNewAnalysis() {
    clearClimateChart();
    resetMapSelection();
    resetAnalysisForm();
    scrollToForm();
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
        .getElementById("latitude")
        .addEventListener("change", handleManualCoordinates);

    document
        .getElementById("longitude")
        .addEventListener("change", handleManualCoordinates);
    document
        .getElementById("scroll-to-form-button")
        .addEventListener("click", handleNewAnalysis);

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
    }
}

window.addEventListener("DOMContentLoaded", initializeApplication);