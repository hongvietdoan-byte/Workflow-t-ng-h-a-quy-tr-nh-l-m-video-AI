"""Nhãn model ảnh theo cùng lựa chọn của ImageRunner; không tạo provider/UI."""
from core import image_models


def image_provider_label(project, provider):
    name = getattr(provider, "name", None)
    name = name.strip() if isinstance(name, str) and name.strip() else None
    model = None
    if getattr(provider, "supports_model", False):
        if project is not None:
            # ImageRunner._submit_kwargs gửi chính giá trị này cho từng project.
            try:
                model = image_models.of_project(project)
            except (AttributeError, KeyError, TypeError):
                model = None
    else:
        # Adapter không nhận model= thì lựa chọn trên project không được gửi.
        model = getattr(provider, "model", None)
    model = model.strip() if isinstance(model, str) and model.strip() else None
    model_text = "model chưa xác định"
    if model:
        try:
            friendly = image_models.label(model)
        except (AttributeError, TypeError, ValueError):
            friendly = None
        model_text = f"{friendly} ({model})" if isinstance(friendly, str) and friendly and friendly != model else model
    mode = " · giả lập" if name and name.casefold().startswith("mock") else " · API thật" if name else ""
    return f"Ảnh: {name or 'nhà cung cấp chưa xác định'} · {model_text}{mode}"
