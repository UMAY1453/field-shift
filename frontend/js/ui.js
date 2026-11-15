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

// Backend ürün kimliklerini kullanıcıya gösterilecek adlarla eşleştirir.
const cropNamesById = new Map([
    ["fallow", "Nadas"],
]);

/**
 * Ürün kimliğine karşılık gelen kullanıcı dostu adı döndürür.
 */
function getCropDisplayName(cropId) {
    if (!cropId) {
        return "Bilinmiyor";
    }

    return cropNamesById.get(cropId) ?? cropId;
}

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
 * Haritadan gelen koordinatları form alanlarına yazar.
 */
export function updateSelectedLocation({ latitude, longitude }) {
    getElement("latitude").value = latitude;
    getElement("longitude").value = longitude;

    getElement("selected-location-text").textContent =
        `${Number(latitude).toFixed(4)}, ${Number(longitude).toFixed(4)}`;
}


/**
 * Backend'den gelen ürünleri üç seçim kutusuna ekler.
 */
export function populateCrops(crops) {
    const previousSelect = getElement("previous-crop");
    const currentSelect = getElement("current-crop");
    const nextSelect = getElement("next-crop");

    // Eski ürün adı eşlemelerini temizler.
    cropNamesById.clear();

    // Nadas yalnızca previous_crop alanında kullanılabilir.
    cropNamesById.set("fallow", "Nadas");

    previousSelect.replaceChildren();
    currentSelect.replaceChildren();
    nextSelect.replaceChildren();

    // Önceki ürün zorunludur; boş seçenek yalnızca açıklamadır.
    const previousPlaceholder = createElement(
        "option",
        "",
        "Önceki ürünü seçin",
    );
    previousPlaceholder.value = "";
    previousPlaceholder.selected = true;
    previousPlaceholder.disabled = true;
    previousSelect.append(previousPlaceholder);

    // Nadas yalnızca önceki ürün listesine eklenir.
    const fallowOption = createElement("option", "", "Nadas");
    fallowOption.value = "fallow";
    previousSelect.append(fallowOption);

    // Değerlendirilecek mevcut ürün zorunludur.
    const currentPlaceholder = createElement(
        "option",
        "",
        "Yetiştirmek istediğiniz ürünü seçin",
    );
    currentPlaceholder.value = "";
    currentPlaceholder.selected = true;
    currentPlaceholder.disabled = true;
    currentSelect.append(currentPlaceholder);

    // Sonraki ürün de güncel backend sözleşmesinde zorunludur.
    const nextPlaceholder = createElement(
        "option",
        "",
        "Sonraki dönem ürününü seçin",
    );
    nextPlaceholder.value = "";
    nextPlaceholder.selected = true;
    nextPlaceholder.disabled = true;
    nextSelect.append(nextPlaceholder);

    crops.forEach((crop) => {
        const label = crop.name ?? crop.id;

        // Sonuç kartlarında Türkçe adı göstermek için saklar.
        cropNamesById.set(crop.id, label);

        const previousOption = createElement("option", "", label);
        previousOption.value = crop.id;
        previousSelect.append(previousOption);

        const currentOption = createElement("option", "", label);
        currentOption.value = crop.id;
        currentSelect.append(currentOption);

        const nextOption = createElement("option", "", label);
        nextOption.value = crop.id;
        nextSelect.append(nextOption);
    });

    const hasCrops = crops.length > 0;

    previousSelect.disabled = !hasCrops;
    currentSelect.disabled = !hasCrops;
    nextSelect.disabled = !hasCrops;
}
/**
 * Ürün listesinin alınamadığını bütün ürün alanlarında belirtir.
 */
export function showCropsUnavailable() {
    const selectIds = [
        "previous-crop",
        "current-crop",
        "next-crop",
    ];

    selectIds.forEach((selectId) => {
        const select = getElement(selectId);
        select.replaceChildren();

        const option = createElement(
            "option",
            "",
            "Ürün listesi alınamadı",
        );

        option.value = "";
        select.append(option);
        select.disabled = true;
    });
}

/**
 * Formu güncel API isteğine uygun nesneye dönüştürür.
 */
export function readAnalysisRequest(form) {
    if (!form.checkValidity()) {
        form.reportValidity();
        throw new Error("Lütfen zorunlu alanları tamamlayın.");
    }

    const latitudeValue = getElement("latitude").value;
    const longitudeValue = getElement("longitude").value;

    if (!latitudeValue || !longitudeValue) {
        throw new Error(
            "Haritadan bir konum seçin veya enlem ve boylamı elle girin.",
        );
    }

    const latitude = Number(latitudeValue);
    const longitude = Number(longitudeValue);

    if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude) ||
        latitude < -90 ||
        latitude > 90 ||
        longitude < -180 ||
        longitude > 180
    ) {
        throw new Error(
            "Enlem -90 ile 90, boylam -180 ile 180 arasında olmalıdır.",
        );
    }

    const harvestStartDate =
        getElement("harvest-start-date").value;

    const harvestEndDate =
        getElement("harvest-end-date").value;

    if (!harvestStartDate || !harvestEndDate) {
        throw new Error(
            "Planlanan hasat başlangıç ve bitiş tarihlerini seçin.",
        );
    }

    if (harvestStartDate > harvestEndDate) {
        throw new Error(
            "Hasat başlangıç tarihi, bitiş tarihinden sonra olamaz.",
        );
    }

    const start = new Date(`${harvestStartDate}T00:00:00Z`);
    const end = new Date(`${harvestEndDate}T00:00:00Z`);

    const harvestPeriodDays =
        Math.floor(
            (end.getTime() - start.getTime()) / 86_400_000,
        ) + 1;

    if (harvestPeriodDays > 120) {
        throw new Error(
            "Planlanan hasat dönemi en fazla 120 gün olabilir.",
        );
    }

    return {
        latitude,
        longitude,

        previous_crop:
            getElement("previous-crop").value,

        current_crop:
            getElement("current-crop").value,

        next_crop:
            getElement("next-crop").value,

        soil_type:
            getElement("soil-type").value,

        priority:
            getElement("priority").value,

        harvest_start_date: harvestStartDate,
        harvest_end_date: harvestEndDate,
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
function createRecommendationCard(
    recommendation,
    index,
    { isPlanned = false } = {},
) {
    const rank = recommendation.rank ?? index + 1;
    const card = createElement(
        "article",
        isPlanned || rank === 1
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
            isPlanned
                ? "Seçtiğiniz plan"
                : rank === 1
                    ? "En uygun öneri"
                    : `${rank}. öneri`,
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
        const cropName = getCropDisplayName(crop);

        rotationPath.append(
            createElement(
                "span",
                "",
                cropIndex === 0
                    ? cropName
                    : `→ ${cropName}`,
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

    appendTextList(
        body,
        "Değerlendirme sınırları",
        recommendation.limitations,
    );

    card.append(header, body);

    return card;
}

/**
 * Kullanıcının seçtiği ürün zincirini önerilerden ayrı gösterir.
 */
function renderPlannedRotationAssessment(assessment) {
    const container = getElement("planned-rotation-assessment");
    container.replaceChildren();

    if (!assessment || typeof assessment !== "object") {
        container.append(
            createElement(
                "div",
                "empty-state",
                "Seçilen ürün planı değerlendirilemedi.",
            ),
        );
        return;
    }

    container.append(
        createRecommendationCard(
            assessment,
            0,
            { isPlanned: true },
        ),
    );
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
    renderPlannedRotationAssessment(
        data.planned_rotation_assessment,
    );
    renderRecommendations(data.recommendations);

    getElement("results-section").hidden = false;
}

/**
 * Yeni analiz için form seçimlerini ve eski sonuç görünümünü temizler.
 */
export function resetAnalysisForm() {
    const form = getElement("analysis-form");

    // Form içindeki seçimleri başlangıç değerlerine döndürür.
    form.reset();

    // Konum alanları formun dışında bulunduğu için ayrıca temizlenir.
    getElement("latitude").value = "";
    getElement("longitude").value = "";

    getElement("selected-location-text").textContent =
        "Henüz konum seçilmedi";

    // Dinamik olarak oluşturulan ürün seçimlerini başlangıca döndürür.
    getElement("previous-crop").value = "";
    getElement("current-crop").value = "";
    getElement("next-crop").value = "";

    // Tarımsal ayarları varsayılan değerlere döndürür.
    getElement("soil-type").value = "";
    getElement("priority").value = "balanced";

    // Hasat tarihlerini yeni analiz için temizler.
    getElement("harvest-start-date").value = "";
    getElement("harvest-end-date").value = "";

    // Önceki hata ve analiz sonuçlarını gizler.
    clearError();
    getElement("results-section").hidden = true;
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