from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]

def test_package_errors_and_repair_controls():
    text = (ROOT / "mockup/tieu_nhi.html").read_text(encoding="utf-8")
    for key in ("packageCheck", "packageList", "addKho", "addPlate", "restorePackage", "generatedHistory", "blockedDemo"):
        assert f'id="{key}"' in text
    assert 'min="0"' in text and 'step="0.01"' in text
    assert "đã gen bản trước" in text and "lần 2" in text
    assert "#24" in text and "Kho 419" in text
    assert 'id="ticketsPanel"' not in text

def test_pet_offline_and_admin_fields():
    text = (ROOT / "mockup/lao_dai_pet.html").read_text(encoding="utf-8")
    for phrase in ("3 ngày", "Nguyên nhân", "Bằng chứng", "Cần gì", "Người làm", "Đã sửa gì", "Test nào", "Mở trên Dashboard", "job kẹt", "gen xong"):
        assert phrase in text
    assert not re.search(r'fetch\(|XMLHttpRequest|https?://', text)
    assert 'id="togglePet"' in text
