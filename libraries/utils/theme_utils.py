from PySide6.QtGui import QColor

from libraries.utils import user_config

# qt_material 在 build_stylesheet 里补齐的语义色（material.css 的 {{danger}}/{{warning}}/{{success}} 同源）
DEFAULT_SEMANTIC_COLORS = {
    'danger': '#dc3545',
    'warning': '#ffc107',
    'success': '#17a2b8',
}

# 视为「无变化」的阈值（dB）
GAIN_COLOR_THRESHOLD = 0.05


# 取当前主题的语义色（danger / warning / success），与 material.css 渲染用的是同一份取值
def get_semantic_color(name: str):
    hex_color = ''
    try:
        from qt_material import get_theme

        theme = get_theme(user_config.get_appearance_theme()) or {}
        hex_color = str(theme.get(name) or '')
    except Exception:
        hex_color = ''
    if not hex_color:
        hex_color = DEFAULT_SEMANTIC_COLORS.get(name, '')
    color = QColor(hex_color)
    return color if color.isValid() else None


# 增益为正、减益为负：分别用主题的 success / danger 作为文字颜色，接近 0 时不标色
def get_gain_text_color(value):
    if value is None or abs(value) < GAIN_COLOR_THRESHOLD:
        return None
    return get_semantic_color('success' if value > 0 else 'danger')
