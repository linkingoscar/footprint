# -*- coding: utf-8 -*-
"""
compress_miniapp_icons.py
-------------------------
一次性工具脚本:压缩微信小程序 tabBar 图标。

背景:
    miniapp/images/ 下的 8 张 tab 图标 PNG 原始尺寸为 1254x1254px、
    每张约 820-881KB(共约 6.8MB),远超微信小程序 tabBar 图标
    40KB 的大小限制,导致小程序无法发布。

做法:
    1. 将每张图缩放到 81x81px(LANCZOS 重采样),保存为优化 PNG,
       直接覆盖原文件。
    2. 若某张图压缩后仍 > 40KB,则依次尝试:
       - quantize() 量化到 256 色(P 模式)
       - 进一步转成 4 位色深(最多 16 色)
       直到满足 <= 40KB 为止。

输出:
    打印每个文件的 before/after 字节数表格。

用法:
    python scripts/compress_miniapp_icons.py [images_dir]
    默认 images_dir 为脚本所在目录的上级目录下的 miniapp/images。
"""

import os
import sys

from PIL import Image

TARGET_SIZE = 81          # 微信 tabBar 图标建议 81x81px
MAX_BYTES = 40 * 1024     # 40KB 上限
LANCZOS = Image.LANCZOS

DEFAULT_IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "miniapp",
    "images",
)


def compress_one(path: str) -> int:
    """把单张 PNG 压缩到 81x81 且 <= 40KB,返回最终字节数。"""
    img = Image.open(path)
    img = img.convert("RGBA")
    img = img.resize((TARGET_SIZE, TARGET_SIZE), LANCZOS)

    # 尝试 1:直接保存优化后的 RGBA PNG
    img.save(path, "PNG", optimize=True)
    if os.path.getsize(path) <= MAX_BYTES:
        return os.path.getsize(path)

    # 尝试 2:量化到 256 色
    img_q = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    img_q.save(path, "PNG", optimize=True)
    if os.path.getsize(path) <= MAX_BYTES:
        return os.path.getsize(path)

    # 尝试 3:转 4 位色深(最多 16 色),仅保留 alpha 为 0/255 的掩码以减小体积
    img_16 = img_q.convert("P", palette=Image.ADAPTIVE, colors=16)
    alpha = img.getchannel("A").point(lambda a: 255 if a > 127 else 0)
    img_16.putalpha(alpha)
    img_16.save(path, "PNG", optimize=True, bits=4)
    if os.path.getsize(path) <= MAX_BYTES:
        return os.path.getsize(path)

    # 最终兜底:直接降低位数到 1 位(纯二值图,通常远小于 40KB)
    img_1 = img_q.convert("P", palette=Image.ADAPTIVE, colors=2)
    img_1.putalpha(alpha)
    img_1.save(path, "PNG", optimize=True, bits=1)
    return os.path.getsize(path)


def main() -> None:
    images_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGES_DIR
    pngs = sorted(
        f for f in os.listdir(images_dir) if f.lower().endswith(".png")
    )
    if not pngs:
        print(f"目录中没有 PNG 文件: {images_dir}")
        sys.exit(1)

    print(f"压缩目录: {images_dir}\n")
    print(f"{'文件':<28}{'原始字节':>12}{'压缩后':>12}{'新尺寸':>10}{'状态':>8}")
    print("-" * 70)

    total_before = 0
    total_after = 0
    all_ok = True

    for name in pngs:
        path = os.path.join(images_dir, name)
        before = os.path.getsize(path)
        after = compress_one(path)

        with Image.open(path) as im:
            size = f"{im.width}x{im.height}"

        ok = after <= MAX_BYTES
        all_ok = all_ok and ok
        status = "OK" if ok else "FAIL"
        total_before += before
        total_after += after
        print(f"{name:<28}{before:>12}{after:>12}{size:>10}{status:>8}")

    print("-" * 70)
    print(
        f"{'合计':<28}{total_before:>12}{total_after:>12}"
        f"{'':>10}{'':>8}"
    )
    print(f"总减小量: {total_before - total_after:,} 字节 "
          f"({(1 - total_after / total_before) * 100:.1f}%)")

    if not all_ok:
        print("\n警告:仍有文件超过 40KB 限制!")
        sys.exit(2)
    print("\n全部文件已满足 <= 40KB 限制。")


if __name__ == "__main__":
    main()
