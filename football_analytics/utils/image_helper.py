"""
image_helper.py
---------------
加载本地球员照片和球队队徽
图片路径: assets/players/{player_id}.png
         assets/teams/{team_id}.png
若图片不存在则返回生成的占位符图片
"""

import os
from datetime import date, datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


# ─────────────────────────────────────────────
# 图片加载
# ─────────────────────────────────────────────

_PLAYER_DIR = "assets/players"
_TEAM_DIR   = "assets/teams"
_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]


def _find_image(directory: str, file_id: int | str) -> str | None:
    """尝试多种扩展名查找图片文件"""
    for ext in _EXTENSIONS:
        path = os.path.join(directory, f"{file_id}{ext}")
        if os.path.exists(path):
            return path
    return None


def _slugify_filename(value: int | str | None) -> str:
    """将名称转换为更稳定的文件名形式，便于按 team_name 查找图片。"""
    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""

    chars = []
    prev_sep = False
    for ch in text:
        if ch.isalnum():
            chars.append(ch)
            prev_sep = False
        elif not prev_sep:
            chars.append("_")
            prev_sep = True

    return "".join(chars).strip("_")


def load_player_image(player_id: int | str, size: tuple[int, int] = (120, 120)) -> Image.Image:
    """
    加载球员照片，调整为指定尺寸
    若不存在则返回带首字母的占位符
    """
    path = _find_image(_PLAYER_DIR, player_id)
    if path:
        try:
            img = Image.open(path).convert("RGBA")
            img = _resize_contain(img, size)
            return img
        except Exception:
            pass
    return _placeholder_image(size, str(player_id)[:1].upper(), "#1a1d2e", "#00d4aa")


def load_team_image(
    team_id: int | str,
    size: tuple[int, int] = (80, 80),
    team_name: str | None = None,
) -> Image.Image:
    """
    加载球队队徽，调整为指定尺寸
    优先按 team_id 查找；若失败则按 team_name 的常见文件名形式兜底。
    若不存在则返回带首字母的占位符
    """
    path = _find_image(_TEAM_DIR, team_id)
    if not path and team_name:
        candidates = [team_name, _slugify_filename(team_name)]
        for candidate in candidates:
            if not candidate:
                continue
            path = _find_image(_TEAM_DIR, candidate)
            if path:
                break

    if path:
        try:
            img = Image.open(path).convert("RGBA")
            img = _resize_contain(img, size)
            return img
        except Exception:
            pass

    placeholder_text = (
        str(team_name).strip()[:1].upper()
        if team_name and str(team_name).strip()
        else str(team_id)[:1].upper()
    )
    return _placeholder_image(size, placeholder_text, "#1a1d2e", "#ff6b35")


# ─────────────────────────────────────────────
# 内部辅助函数
# ─────────────────────────────────────────────

def _resize_contain(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """等比缩放并居中填充到目标尺寸（保持宽高比）"""
    img.thumbnail(size, Image.LANCZOS)
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
    result.paste(img, offset)
    return result


def _placeholder_image(
    size: tuple[int, int],
    text: str,
    bg_color: str,
    fg_color: str,
) -> Image.Image:
    """生成带文字的占位符图片（圆角矩形背景）"""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 绘制圆角矩形背景
    padding = 2
    _draw_rounded_rect(draw, padding, padding, size[0] - padding, size[1] - padding, 12, bg_color)

    # 绘制文字
    font_size = int(min(size) * 0.4)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size[0] - text_w) // 2
    y = (size[1] - text_h) // 2
    draw.text((x, y), text, fill=fg_color, font=font)

    return img


def _draw_rounded_rect(
    draw: ImageDraw.Draw,
    x0: int, y0: int, x1: int, y1: int,
    radius: int,
    fill: str,
) -> None:
    """在 ImageDraw 上绘制圆角矩形"""
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.ellipse([x0, y0, x0 + 2 * radius, y0 + 2 * radius], fill=fill)
    draw.ellipse([x1 - 2 * radius, y0, x1, y0 + 2 * radius], fill=fill)
    draw.ellipse([x0, y1 - 2 * radius, x0 + 2 * radius, y1], fill=fill)
    draw.ellipse([x1 - 2 * radius, y1 - 2 * radius, x1, y1], fill=fill)


# ─────────────────────────────────────────────
# 日期辅助
# ─────────────────────────────────────────────

def compute_age(birth_date) -> int | None:
    """从出生日期计算年龄"""
    if birth_date is None or (isinstance(birth_date, float) and np.isnan(birth_date)):
        return None
    try:
        if isinstance(birth_date, (date, datetime)):
            bd = birth_date if isinstance(birth_date, date) else birth_date.date()
        else:
            bd = datetime.strptime(str(birth_date)[:10], "%Y-%m-%d").date()
        today = date.today()
        return (today - bd).days // 365
    except Exception:
        return None


def format_birth_date(birth_date) -> str:
    """格式化出生日期为 DD Mon YYYY"""
    if birth_date is None:
        return "N/A"
    try:
        if isinstance(birth_date, (date, datetime)):
            bd = birth_date
        else:
            bd = datetime.strptime(str(birth_date)[:10], "%Y-%m-%d")
        return bd.strftime("%d %b %Y")
    except Exception:
        return "N/A"


def get_player_display_name(row: pd.Series) -> str:
    """
    球员显示名称（用于下拉框、标题、图表标签等所有场景）
    优先级：player_known_name → player_name → Unknown
    ⚠️  不拼接 first_name + last_name，避免 'None None'/'nan nan' 问题
        first/last name 只在需要显示表格全名时单独取用
    """
    def _clean(val) -> str:
        """安全转字符串，过滤 None / NaN / 字面量 'none'/'nan'"""
        if val is None:
            return ""
        if isinstance(val, float) and np.isnan(val):
            return ""
        s = str(val).strip()
        return "" if s.lower() in ("none", "nan", "") else s

    return (
        _clean(row.get("player_known_name"))
        or _clean(row.get("player_name"))
        or "Unknown"
    )


def get_player_full_name_parts(row: pd.Series) -> tuple[str, str]:
    """
    仅在需要表格中分列显示姓/名时调用
    返回 (first_name, last_name)，安全处理 None/NaN
    """
    def _clean(val) -> str:
        if val is None:
            return ""
        if isinstance(val, float) and np.isnan(val):
            return ""
        s = str(val).strip()
        return "" if s.lower() in ("none", "nan", "") else s

    return (
        _clean(row.get("player_first_name")),
        _clean(row.get("player_last_name")),
    )
