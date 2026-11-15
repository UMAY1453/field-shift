"""Ürün rotasyonu değerlendirme ve öneri yardımcıları."""

#Kişi-2'nin ana branchinden gelen verileri değerlendirmede kullanılacak sıralamasını hazırlamak 
#Bu pre veya next kısmı yoksa diye
def build_rotation_path(
    previous_crop: str | None,
    candidate_crop: str,
    next_crop: str | None,
) -> list[str]:
    """Bilinen ürünleri tarımsal sıralarını koruyarak döndürür.

    ``candidate_crop`` kullanıcının seçtiği mevcut aday veya algoritmanın
    değerlendirdiği alternatif üründür. Önceki ürün bilinmiyorsa ve sonraki ürün
    planlanmamışsa bu değerler rotasyon yoluna eklenmez. ``fallow`` bilinmeyen
    geçmişten farklı, bilinen bir arazi durumu olduğu için korunur.
    """

    if not isinstance(candidate_crop, str) or not candidate_crop.strip():
        raise ValueError("Değerlendirilecek ürün kimliği boş olamaz.")

    rotation = []

    if previous_crop is not None:
        rotation.append(previous_crop)

    rotation.append(candidate_crop)

    if next_crop is not None:
        rotation.append(next_crop)

    return rotation


#Bu 3 lüyü pre-candidate   /    candidate - next diye ayırır
def build_rotation_pairs(rotation: list[str]) -> list[tuple[str, str]]:
    """Rotasyon yolundaki birbirini izleyen ürün çiftlerini döndürür."""

    return list(zip(rotation, rotation[1:]))