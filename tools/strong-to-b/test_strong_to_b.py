"""
Tests cho engine strong_to_b — viết TRƯỚC khi implement (TDD).

Quy ước:
- convert(html) -> (new_html, report)
- report là dict: total, converted, protected, protected_heading, protected_link
- Nguyên tắc CỐT LÕI: chỉ đổi <strong>/<​/strong> KHÔNG nằm trong vùng cấm.
  Vùng cấm = strong có tổ tiên h1-h6/a, HOẶC strong chứa hậu duệ <a>.
- Mọi byte khác giữ NGUYÊN.
"""
import pytest
from strong_to_b import convert


# ---------- ĐỔI (không vùng cấm) ----------

def test_paragraph_converts():
    out, rep = convert("<p><strong>Lưu ý:</strong> Bảng giá</p>")
    assert out == "<p><b>Lưu ý:</b> Bảng giá</p>"
    assert rep["converted"] == 1
    assert rep["total"] == 1

def test_li_without_link_converts():
    out, _ = convert("<li><strong>Chất liệu nhôm:</strong> Bền bỉ</li>")
    assert out == "<li><b>Chất liệu nhôm:</b> Bền bỉ</li>"

def test_td_converts():
    out, _ = convert("<td><strong>800.000 USD</strong></td>")
    assert out == "<td><b>800.000 USD</b></td>"

def test_label_converts():
    out, _ = convert("<label><strong>Họ tên</strong></label>")
    assert out == "<label><b>Họ tên</b></label>"


# ---------- GIỮ NGUYÊN: heading ----------

@pytest.mark.parametrize("h", ["h1", "h2", "h3", "h4", "h5", "h6"])
def test_heading_protects(h):
    src = f"<{h}><strong>Bước 4</strong></{h}>"
    out, rep = convert(src)
    assert out == src
    assert rep["converted"] == 0
    assert rep["protected_heading"] == 1


# ---------- GIỮ NGUYÊN: link, cả 2 chiều lồng ----------

def test_strong_inside_link_protects():
    src = '<a href="/gia"><strong>giá in tem</strong></a>'
    out, rep = convert(src)
    assert out == src
    assert rep["protected_link"] == 1

def test_link_inside_strong_protects():
    # a nằm trong strong -> giữ nguyên cả cụm
    src = '<p><strong>xem <a href="/x">tại đây</a> ngay</strong></p>'
    out, rep = convert(src)
    assert out == src
    assert rep["converted"] == 0
    assert rep["protected_link"] == 1


# ---------- Giữ attribute khi đổi ----------

def test_preserves_attributes():
    out, _ = convert('<p><strong class="hl" data-x="1">A</strong></p>')
    assert out == '<p><b class="hl" data-x="1">A</b></p>'


# ---------- Không đụng <b> có sẵn ----------

def test_existing_b_untouched():
    src = "<p><b>đã là b</b> và <strong>strong</strong></p>"
    out, _ = convert(src)
    assert out == "<p><b>đã là b</b> và <b>strong</b></p>"


# ---------- Không đụng vùng raw ----------

def test_script_block_untouched():
    src = '<script>var s="<strong>x</strong>";</script><p><strong>Y</strong></p>'
    out, _ = convert(src)
    assert out == '<script>var s="<strong>x</strong>";</script><p><b>Y</b></p>'

def test_style_block_untouched():
    src = "<style>.a{}</style><p><strong>Z</strong></p>"
    out, _ = convert(src)
    assert out == "<style>.a{}</style><p><b>Z</b></p>"

def test_comment_untouched():
    src = "<!-- <strong>giấu</strong> --><p><strong>thật</strong></p>"
    out, _ = convert(src)
    assert out == "<!-- <strong>giấu</strong> --><p><b>thật</b></p>"


# ---------- Strong lồng strong ----------

def test_nested_strong_both_convert():
    src = "<p><strong>ngoài <strong>trong</strong></strong></p>"
    out, rep = convert(src)
    assert out == "<p><b>ngoài <b>trong</b></b></p>"
    assert rep["converted"] == 2

def test_nested_strong_inside_link_both_protected():
    src = '<a href="/x"><strong>a <strong>b</strong></strong></a>'
    out, rep = convert(src)
    assert out == src
    assert rep["converted"] == 0


# ---------- Byte-preservation: whitespace / newline ----------

def test_whitespace_preserved():
    src = "<p>\n   <strong>A</strong>\n</p>"
    out, _ = convert(src)
    assert out == "<p>\n   <b>A</b>\n</p>"

def test_uppercase_tag_converts():
    # WP đôi khi xuất hoa
    out, _ = convert("<P><STRONG>A</STRONG></P>")
    assert out == "<P><b>A</b></P>"


# ---------- Idempotent ----------

def test_idempotent():
    src = '<h2><strong>Giữ</strong></h2><p><strong>Đổi</strong> <a><strong>link</strong></a></p>'
    once, _ = convert(src)
    twice, _ = convert(once)
    assert once == twice


# ---------- Thẻ thiếu đóng (lenient) ----------

def test_unclosed_strong_does_not_crash():
    src = "<p><strong>chưa đóng</p>"
    out, rep = convert(src)
    # strong không có close -> không đổi (an toàn), không crash
    assert "chưa đóng" in out

def test_empty_and_no_strong():
    assert convert("") == ("", {"total": 0, "converted": 0, "protected": 0,
                                "protected_heading": 0, "protected_link": 0})
    out, rep = convert("<p>không có gì</p>")
    assert out == "<p>không có gì</p>"
    assert rep["total"] == 0


# ---------- Report breakdown ----------

def test_report_breakdown():
    src = ("<h2><strong>A</strong></h2>"
           "<p><strong>B</strong></p>"
           '<a href="/x"><strong>C</strong></a>'
           "<li><strong>D</strong></li>")
    _, rep = convert(src)
    assert rep["total"] == 4
    assert rep["converted"] == 2          # B, D
    assert rep["protected"] == 2          # A, C
    assert rep["protected_heading"] == 1  # A
    assert rep["protected_link"] == 1     # C
