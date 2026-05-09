"""
tests/test_preprocessor.py

Unit test cho TextPreprocessor — bao gồm các đoạn văn mẫu có ký tự lạ,
emoji, HTML entities, số, stopwords tiếng Việt và tiếng Anh.
"""

import pytest
from ingestion.preprocessor import TextPreprocessor, ALL_STOPWORDS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def prep() -> TextPreprocessor:
    return TextPreprocessor()


@pytest.fixture
def prep_keep_numbers() -> TextPreprocessor:
    return TextPreprocessor(keep_numbers=True)


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_lowercase(self, prep):
        assert prep.normalize("Hello WORLD") == "hello world"

    def test_unicode_nfc(self, prep):
        # "ă" có thể được biểu diễn bằng 2 codepoint (NFD) hoặc 1 codepoint (NFC)
        nfd_text = "a\u0306"  # a + combining breve = ă (NFD)
        assert prep.normalize(nfd_text) == "ă"

    def test_remove_special_chars(self, prep):
        result = prep.normalize("Giá: 1.000đ! (khuyến mãi) #sale @2024")
        assert "!" not in result
        assert "#" not in result
        assert "@" not in result
        assert "." not in result
        assert "(" not in result

    def test_remove_emoji(self, prep):
        result = prep.normalize("Hôm nay trời đẹp 😊🌟 quá!")
        assert "😊" not in result
        assert "🌟" not in result
        assert "hôm nay trời đẹp" in result

    def test_remove_html_like_tags(self, prep):
        # Ký tự < > bị loại bỏ, chữ cái còn lại
        result = prep.normalize("<b>Tiêu đề</b>")
        assert "<" not in result
        assert ">" not in result
        assert "tiêu đề" in result

    def test_collapse_whitespace(self, prep):
        assert prep.normalize("   nhiều   khoảng   trắng   ") == "nhiều khoảng trắng"

    def test_underscore_removed(self, prep):
        result = prep.normalize("snake_case_variable")
        assert "_" not in result

    def test_non_string_raises(self, prep):
        with pytest.raises(TypeError):
            prep.normalize(12345)  # type: ignore

    def test_empty_string(self, prep):
        assert prep.normalize("") == ""

    def test_only_special_chars(self, prep):
        assert prep.normalize("!@#$%^&*()") == ""

    def test_mixed_vn_en(self, prep):
        result = prep.normalize("Học Machine Learning tại Hà Nội 2024!")
        assert result == "học machine learning tại hà nội 2024"


# ---------------------------------------------------------------------------
# tokenize()
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_basic_split(self, prep):
        tokens = prep.tokenize("xin chào thế giới")
        assert tokens == ["xin", "chào", "thế", "giới"]

    def test_normalizes_before_split(self, prep):
        tokens = prep.tokenize("Hello, World! 123.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "123" in tokens

    def test_empty_returns_empty_list(self, prep):
        assert prep.tokenize("") == []

    def test_special_chars_only(self, prep):
        assert prep.tokenize("!!!---@@@") == []

    def test_tokenize_vn_text(self, prep):
        tokens = prep.tokenize("Đây là một đoạn văn bản tiếng Việt.")
        assert "đây" in tokens
        assert "văn" in tokens
        assert "bản" in tokens

    def test_tokenize_number_kept_as_token(self, prep):
        tokens = prep.tokenize("Năm 2024 có nhiều sự kiện")
        assert "2024" in tokens


# ---------------------------------------------------------------------------
# remove_stopwords()
# ---------------------------------------------------------------------------

class TestRemoveStopwords:
    def test_removes_vn_stopwords(self, prep):
        tokens = ["đây", "là", "văn", "bản", "của", "tôi"]
        result = prep.remove_stopwords(tokens)
        assert "là" not in result
        assert "của" not in result
        assert "tôi" not in result
        assert "văn" in result
        assert "bản" in result

    def test_removes_en_stopwords(self, prep):
        tokens = ["this", "is", "a", "test", "document"]
        result = prep.remove_stopwords(tokens)
        assert "this" not in result
        assert "is" not in result
        assert "a" not in result
        assert "test" in result
        assert "document" in result

    def test_min_length_filter(self, prep):
        # min_token_length=2 mặc định → bỏ token 1 ký tự
        tokens = ["a", "be", "cat"]
        result = prep.remove_stopwords(tokens)
        assert "a" not in result  # độ dài 1

    def test_removes_pure_numbers_by_default(self, prep):
        tokens = ["2024", "học", "tập"]
        result = prep.remove_stopwords(tokens)
        assert "2024" not in result

    def test_keep_numbers_flag(self, prep_keep_numbers):
        tokens = ["2024", "học", "tập"]
        result = prep_keep_numbers.remove_stopwords(tokens)
        assert "2024" in result

    def test_custom_stopwords(self):
        custom_prep = TextPreprocessor(stopwords={"custom", "stop"})
        tokens = ["custom", "word", "stop", "here"]
        result = custom_prep.remove_stopwords(tokens)
        assert "custom" not in result
        assert "stop" not in result
        assert "word" in result
        assert "here" in result

    def test_empty_list(self, prep):
        assert prep.remove_stopwords([]) == []


# ---------------------------------------------------------------------------
# process()  — full pipeline
# ---------------------------------------------------------------------------

class TestProcess:
    def test_full_pipeline_vn(self, prep):
        text = "Đây là một đoạn văn bản tiếng Việt, có các ký tự đặc biệt như: !@#$."
        tokens = prep.process(text)
        # Stopwords bị loại
        assert "là" not in tokens
        assert "một" not in tokens
        assert "các" not in tokens
        # Ký tự đặc biệt bị loại
        assert "!" not in tokens
        # Từ có nghĩa được giữ
        assert "đoạn" in tokens
        assert "tiếng" in tokens
        assert "việt" in tokens

    def test_full_pipeline_en(self, prep):
        text = "The quick brown fox jumps over the lazy dog."
        tokens = prep.process(text)
        assert "the" not in tokens
        assert "over" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

    def test_pipeline_with_emoji_and_html(self, prep):
        text = "Sản phẩm <b>tốt</b> nhất 😍 giá rẻ!!!"
        tokens = prep.process(text)
        assert "😍" not in tokens
        assert "!!!" not in tokens
        assert "tốt" in tokens
        assert "giá" in tokens

    def test_pipeline_mixed_language(self, prep):
        text = "Học Machine Learning với Python là rất thú vị!"
        tokens = prep.process(text)
        assert "là" not in tokens
        assert "rất" not in tokens
        assert "machine" in tokens
        assert "learning" in tokens
        assert "python" in tokens
        assert "thú" in tokens
        assert "vị" in tokens

    def test_pipeline_empty(self, prep):
        assert prep.process("") == []

    def test_pipeline_only_stopwords(self, prep):
        text = "và của là có trong cho với các"
        assert prep.process(text) == []

    def test_pipeline_repeated_spaces_and_newlines(self, prep):
        text = "dòng   đầu\n\ndòng   thứ   hai\t\t tab"
        tokens = prep.process(text)
        assert "dòng" in tokens
        assert "đầu" in tokens
        assert "hai" in tokens
        assert "tab" in tokens

    def test_pipeline_long_text(self, prep):
        text = (
            "Hệ thống t            git add core/ingestion/preprocessor.py
            git commit -m "Mô tả thay đổi của bạn"ìm kiếm thông tin (Information Retrieval) là một lĩnh vực "
            "nghiên cứu trong khoa học máy tính, tập trung vào việc tổ chức, "
            "lưu trữ và truy xuất thông tin từ các kho văn bản lớn. "
            "Các thuật toán như TF-IDF và BM25 được sử dụng rộng rãi."
        )
        tokens = prep.process(text)
        assert len(tokens) > 5
        assert "tìm" in tokens
        assert "kiếm" in tokens
        assert "thông" in tokens
        assert "thuật" in tokens
        # Stopwords không được lọt qua
        assert "là" not in tokens
        assert "và" not in tokens
        assert "các" not in tokens