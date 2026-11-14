const numberFormatter = new Intl.NumberFormat("tr-TR", {
    maximumFractionDigits: 1,
});

const riskLabels = {
    low: "Düşük",
    medium: "Orta",
    high: "Yüksek",
};

const sourceDescriptions = {
    live: "Analiz canlı NASA POWER verileriyle oluşturuldu.",
    cache: "Analiz daha önce alınmış NASA POWER verileriyle oluşturuldu.",
    demo: "NASA servisine ulaşılamadığı için demo veri kullanıldı.",
};

/**
 * Tekrarlanan DOM sorgularını kısaltır.
 */
function getElement(id) {
    return document.getElementById(id);
}

/**
 * Sayısal değerleri Türkçe sayı biçiminde gösterir.
 */
function formatNumber(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "—";
    }

    return numberFormatter.format(Number(value));
}

/**
 * Güvenli bir DOM elemanı oluşturur.
 */
function createElement(tagName, className, textContent) {
    const element = document.createElement(tagName);

    if (className) {
        element.className = className;
    }

    if (textContent !== undefined) {
        element.textContent = textContent;
    }

    return element;
}

/**
 * Tarihi input alanlarının istediği YYYY-MM-DD biçimine dönüştürür.
 */
function toDateInputValue(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

/**
 * NASA verisinin gecikmesini dikkate alarak son bir yıllık aralık seçer.
 */
export function setDefaultDateRange() {
    const endDate = new Date();

    // Günlük verilerin tamamlanması için son yedi gün dışarıda bırakılır.
    endDate.setDate(endDate.getDate() - 7);

    const startDate = new Date(endDate);
    startDate.setFullYear(startDate.getFullYear() - 1);
    startDate.setDate(startDate.getDate() + 1);

    const startInput = getElement("start-date");
    const endInput = getElement("end-date");

    startInput.value = toDateInputValue(startDate);
    endInput.value = toDateInputValue(endDate);
    endInput.max = toDateInputValue(endDate);
}

/**
 * Haritadan gelen koordinatları form alanlarına yazar.
 */
export function updateSelectedLocation({ latitude, longitude }) {
    getElement("latitude").value = latitude;
    getElement("longitude").value = longitude;

    getElement("selected-location-text").textContent =
        `${Number(latitude).toFixed(4)}, ${Number(longitude).toFixed(4)}`;
}

/**
 * Backend bağlantı durumunu üst menüde gösterir.
 */
export function setApiStatus(status) {
    const container = getElement("api-status");
    const text = getElement("api-status-text");

    container.classList.remove(
        "api-status--checking",
        "api-status--online",
        "api-status--offline",
    );

    if (status === "online") {
        container.classList.add("api-status--online");
        text.textContent = "Backend bağlı";
        return;
    }

    if (status === "offline") {
        container.classList.add("api-status--offline");
        text.textContent = "Backend bağlantısı yok";
        return;
    }

    container.classList.add("api-status--checking");
    text.textContent = "Backend kontrol ediliyor";
}

/**
 * Backend'den gelen ürünleri seçim kutusuna ekler.
 */
export function populateCrops(crops) {
    const select = getElement("current-crop");
    select.replaceChildren();

    const placeholder = createElement(
        "option",
        "",
        "Mevcut ürününüzü seçin",
    );

    placeholder.value = "";
    placeholder.selected = true;
    placeholder.disabled = true;
    select.append(placeholder);

    crops.forEach((crop) => {
        const option = createElement(
            "option",
            "",
            crop.name ?? crop.id,
        );

        option.value = crop.id;
        select.append(option);
    });

    select.disabled = crops.length === 0;
}

/**
 * Ürün listesinin alınamadığını form üzerinde belirtir.
 */
export function showCropsUnavailable() {
    const select = getElement("current-crop");
    select.replaceChildren();

    const option = createElement(
        "option",
        "",
        "Ürün listesi alınamadı",
    );

    option.value = "";
    select.append(option);
    select.disabled = true;
}

/**
 * Formu API isteği için uygun nesneye dönüştürür.
 */
export function readAnalysisRequest(form) {
    if (!form.checkValidity()) {
        form.reportValidity();
        throw new Error("Lütfen zorunlu alanları tamamlayın.");
    }

    const latitude = Number(getElement("latitude").value);
    const longitude = Number(getElement("longitude").value);
    const startDate = getElement("start-date").value;
    const endDate = getElement("end-date").value;

    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        throw new Error("Lütfen haritadan bir konum seçin.");
    }

    if (startDate > endDate) {
        throw new Error(
            "Başlangıç tarihi, bitiş tarihinden sonra olamaz.",
        );
    }

    return {
        latitude,
        longitude,
        start_date: startDate,
        end_date: endDate,
        current_crop: getElement("current-crop").value,
        soil_type: getElement("soil-type").value,
        priority: getElement("priority").value,
    };
}

/**
 * Ekrandaki hata kutusunu gösterir.
 */
export function showError(message) {
    const errorContainer = getElement("error-message");
    errorContainer.textContent = message;
    errorContainer.hidden = false;
}

/**
 * Önceki hata mesajını temizler.
 */
export function clearError() {
    const errorContainer = getElement("error-message");
    errorContainer.textContent = "";
    errorContainer.hidden = true;
}

/**
 * Analiz devam ederken formu ve yükleme katmanını yönetir.
 */
export function setLoading(isLoading) {
    const overlay = getElement("loading-overlay");
    const form = getElement("analysis-form");
    const button = getElement("analyze-button");
    const buttonText = button.querySelector("span");

    overlay.hidden = !isLoading;
    button.disabled = isLoading;
    form.setAttribute("aria-busy", String(isLoading));

    buttonText.textContent = isLoading
        ? "Analiz hazırlanıyor"
        : "İklim analizini başlat";
}

/**
 * Veri kaynağının canlı, cache veya demo olduğunu gösterir.
 */
function renderSource(source = {}) {
    const mode = source.mode ?? "demo";
    const banner = getElement("source-banner");

    banner.dataset.mode = mode;
    getElement("source-mode").textContent = mode.toUpperCase();
    getElement("source-title").textContent =
        source.name ?? "NASA POWER";

    getElement("source-description").textContent =
        sourceDescriptions[mode] ??
        "Analizde kullanılan veri kaynağı bildirildi.";
}

/**
 * İklim özet kartlarını doldurur.
 */
function renderSummary(summary = {}) {
    getElement("average-temperature").textContent =
        formatNumber(summary.average_temperature_c);

    getElement("temperature-range").textContent =
        `Min ${formatNumber(summary.minimum_temperature_c)} °C / ` +
        `Maks ${formatNumber(summary.maximum_temperature_c)} °C`;

    getElement("total-precipitation").textContent =
        formatNumber(summary.total_precipitation_mm);

    getElement("dry-days").textContent =
        formatNumber(summary.dry_days);

    getElement("longest-dry-spell").textContent =
        formatNumber(summary.longest_dry_spell_days);

    getElement("data-completeness").textContent =
        formatNumber(summary.data_completeness_percent);
}

/**
 * Risk seviyesini ve risk nedenlerini gösterir.
 */
function renderRisk(risk = {}) {
    const level = risk.level ?? "medium";
    const badge = getElement("risk-level");
    const reasonsContainer = getElement("risk-reasons");

    getElement("risk-score").textContent =
        formatNumber(risk.score);

    badge.className = `risk-badge risk-badge--${level}`;
    badge.textContent = riskLabels[level] ?? level;

    reasonsContainer.replaceChildren();

    const reasons = Array.isArray(risk.reasons)
        ? risk.reasons
        : [];

    if (reasons.length === 0) {
        reasonsContainer.append(
            createElement(
                "li",
                "",
                "Belirgin bir risk gerekçesi bildirilmedi.",
            ),
        );
        return;
    }

    reasons.forEach((reason) => {
        reasonsContainer.append(
            createElement("li", "", reason),
        );
    });
}

/**
 * Öneri kartına bir puan satırı ekler.
 */
function createScoreRow(label, score) {
    const safeScore = Math.max(
        0,
        Math.min(100, Number(score) || 0),
    );

    const row = createElement("div", "score-row");
    const labelElement = createElement("span", "", label);
    const track = createElement("div", "score-row__track");
    const fill = createElement("div", "score-row__fill");
    const value = createElement("strong", "", String(safeScore));

    fill.style.width = `${safeScore}%`;
    track.append(fill);
    row.append(labelElement, track, value);

    return row;
}

/**
 * Avantaj veya risk maddelerini karta ekler.
 */
function appendTextList(container, title, items, isRisk = false) {
    if (!Array.isArray(items) || items.length === 0) {
        return;
    }

    container.append(
        createElement(
            "strong",
            "recommendation-section-title",
            title,
        ),
    );

    const list = createElement(
        "ul",
        isRisk
            ? "recommendation-list recommendation-list--risk"
            : "recommendation-list",
    );

    items.forEach((item) => {
        list.append(createElement("li", "", item));
    });

    container.append(list);
}

/**
 * Tek bir ürün rotasyonu öneri kartı oluşturur.
 */
function createRecommendationCard(recommendation, index) {
    const rank = recommendation.rank ?? index + 1;
    const card = createElement(
        "article",
        rank === 1
            ? "recommendation-card recommendation-card--featured"
            : "recommendation-card",
    );

    const header = createElement(
        "div",
        "recommendation-card__header",
    );

    const headingGroup = createElement("div");
    headingGroup.append(
        createElement(
            "span",
            "recommendation-rank",
            rank === 1 ? "En uygun öneri" : `${rank}. öneri`,
        ),
        createElement(
            "h3",
            "",
            recommendation.crop_name ??
                recommendation.crop_id ??
                "Ürün",
        ),
    );

    const totalScore = recommendation.scores?.total ?? 0;
    const scoreBadge = createElement(
        "span",
        "recommendation-score",
        String(totalScore),
    );

    header.append(headingGroup, scoreBadge);

    const body = createElement(
        "div",
        "recommendation-card__body",
    );

    const rotationPath = createElement("div", "rotation-path");

    const rotation = Array.isArray(recommendation.rotation)
        ? recommendation.rotation
        : [];

    rotation.forEach((crop, cropIndex) => {
        rotationPath.append(
            createElement(
                "span",
                "",
                cropIndex === 0 ? crop : `→ ${crop}`,
            ),
        );
    });

    const scoreList = createElement("div", "score-list");
    const scores = recommendation.scores ?? {};

    scoreList.append(
        createScoreRow("İklim", scores.climate),
        createScoreRow("Su", scores.water),
        createScoreRow("Toprak", scores.soil),
        createScoreRow("Rotasyon", scores.rotation),
    );

    body.append(rotationPath, scoreList);

    appendTextList(
        body,
        "Avantajlar",
        recommendation.advantages,
    );

    appendTextList(
        body,
        "Dikkat edilmesi gerekenler",
        recommendation.risks,
        true,
    );

    card.append(header, body);

    return card;
}

/**
 * Bütün öneri kartlarını ekrana yerleştirir.
 */
function renderRecommendations(recommendations) {
    const container = getElement("recommendations");
    container.replaceChildren();

    if (
        !Array.isArray(recommendations) ||
        recommendations.length === 0
    ) {
        container.append(
            createElement(
                "div",
                "empty-state",
                "Bu koşullar için uygun bir rotasyon önerisi üretilemedi.",
            ),
        );
        return;
    }

    recommendations.forEach((recommendation, index) => {
        container.append(
            createRecommendationCard(recommendation, index),
        );
    });
}

/**
 * API analiz cevabını sonuç bölümüne aktarır.
 */
export function renderAnalysisResult(data) {
    if (!data || typeof data !== "object") {
        throw new Error("Backend geçerli bir analiz sonucu döndürmedi.");
    }

    const location = data.location ?? {};
    const locationLabel =
        location.label ||
        `${formatNumber(location.latitude)}, ${formatNumber(location.longitude)}`;

    getElement("results-location").textContent =
        `${locationLabel} için iklim ve rotasyon sonuçları.`;

    renderSource(data.source);
    renderSummary(data.summary);
    renderRisk(data.risk);
    renderRecommendations(data.recommendations);

    getElement("results-section").hidden = false;
}

/**
 * Sonuç bölümüne yumuşak kaydırma yapar.
 */
export function scrollToResults() {
    getElement("results-section").scrollIntoView({
        behavior: "smooth",
        block: "start",
    });
}

/**
 * Yeni analiz için form alanına geri döner.
 */
export function scrollToForm() {
    getElement("analysis-form").scrollIntoView({
        behavior: "smooth",
        block: "center",
    });
}