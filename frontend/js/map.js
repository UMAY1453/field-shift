let mapInstance = null;
let selectedMarker = null;
let locationChangeHandler = null;

// Haritanın Türkiye merkezli başlangıç görünümü.
const DEFAULT_CENTER = [39.0, 35.0];
const DEFAULT_ZOOM = 6;

/**
 * Enlem ve boylamı altı ondalık basamakla sınırlar.
 */
function roundCoordinate(value) {
    return Number(Number(value).toFixed(6));
}

/**
 * Seçilen noktaya marker ekler ve formu bilgilendirir.
 */
function selectLocation(latitude, longitude, shouldZoom = true) {
    const lat = roundCoordinate(latitude);
    const lng = roundCoordinate(longitude);

    if (!selectedMarker) {
        selectedMarker = window.L.marker([lat, lng], {
            draggable: true,
            title: "Seçilen tarım alanı",
        }).addTo(mapInstance);

        // Marker sürüklendiğinde koordinatları yeniden hesaplar.
        selectedMarker.on("dragend", (event) => {
            const position = event.target.getLatLng();
            selectLocation(position.lat, position.lng, false);
        });
    } else {
        selectedMarker.setLatLng([lat, lng]);
    }

    selectedMarker
        .bindPopup(
            `<strong>Seçilen konum</strong><br>${lat.toFixed(4)}, ${lng.toFixed(4)}`,
        )
        .openPopup();

    if (shouldZoom) {
        mapInstance.setView([lat, lng], 11);
    }

    // app.js içindeki konum güncelleme fonksiyonunu çağırır.
    locationChangeHandler?.({
        latitude: lat,
        longitude: lng,
    });
}

/**
 * Leaflet haritasını oluşturur.
 */
export function initializeMap(onLocationChange) {
    if (!window.L) {
        throw new Error("Leaflet kütüphanesi yüklenemedi.");
    }

    const mapContainer = document.getElementById("map");

    if (!mapContainer) {
        throw new Error("Harita alanı bulunamadı.");
    }

    locationChangeHandler = onLocationChange;

    // HTML içindeki geçici yükleme mesajını temizler.
    mapContainer.replaceChildren();

    mapInstance = window.L.map(mapContainer, {
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        minZoom: 3,
        maxZoom: 18,
        zoomControl: true,
    });

    // OpenStreetMap görüntülerini haritaya ekler.
    window.L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        },
    ).addTo(mapInstance);

    // Kullanıcının haritada tıkladığı konumu seçer.
    mapInstance.on("click", (event) => {
        selectLocation(event.latlng.lat, event.latlng.lng);
    });

    return mapInstance;
}

/**
 * Tarayıcıdan kullanıcının mevcut konum iznini ister.
 */
export function useCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(
                new Error("Tarayıcınız konum özelliğini desteklemiyor."),
            );
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const coordinates = {
                    latitude: roundCoordinate(position.coords.latitude),
                    longitude: roundCoordinate(position.coords.longitude),
                };

                selectLocation(
                    coordinates.latitude,
                    coordinates.longitude,
                );

                resolve(coordinates);
            },
            (error) => {
                const errorMessages = {
                    1: "Konum izni reddedildi.",
                    2: "Mevcut konum belirlenemedi.",
                    3: "Konum isteği zaman aşımına uğradı.",
                };

                reject(
                    new Error(
                        errorMessages[error.code] ??
                            "Konum alınırken bir hata oluştu.",
                    ),
                );
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000,
            },
        );
    });
}

/**
 * Ekran boyutu değiştiğinde Leaflet ölçülerini yeniler.
 */
export function invalidateMapSize() {
    mapInstance?.invalidateSize();
}

/**
 * Seçilen konumu kaldırır ve haritayı başlangıç görünümüne döndürür.
 */
export function resetMapSelection() {
    if (selectedMarker) {
        selectedMarker.remove();
        selectedMarker = null;
    }

    mapInstance?.setView(
        DEFAULT_CENTER,
        DEFAULT_ZOOM,
    );
}