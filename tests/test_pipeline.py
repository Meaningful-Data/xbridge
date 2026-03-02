"""Tests for the validate-convert-validate pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from xbridge.api import convert_instance
from xbridge.exceptions import ValidationError

NO_ERRORS: dict = {"errors": {}, "warnings": {}}
PRE_ERRORS: dict = {
    "errors": {
        "XML-001": [
            {
                "rule_id": "XML-001",
                "severity": "ERROR",
                "message": "Missing schemaRef",
                "location": "instance.xbrl",
            }
        ]
    },
    "warnings": {},
}
POST_ERRORS: dict = {
    "errors": {
        "CSV-001": [
            {
                "rule_id": "CSV-001",
                "severity": "ERROR",
                "message": "Bad CSV structure",
                "location": "report.zip",
            }
        ]
    },
    "warnings": {},
}

_VALIDATE = "xbridge.validation.validate"
_CONVERTER = "xbridge.api.Converter"


class TestPipelineValidateTrue:
    """Pipeline behaviour when validate=True."""

    @patch(_CONVERTER)
    @patch(_VALIDATE)
    def test_valid_file_converts_ok(
        self, mock_validate: MagicMock, mock_converter_cls: MagicMock, tmp_path: Path
    ) -> None:
        """No validation errors -> conversion runs and returns path."""
        mock_validate.return_value = NO_ERRORS
        output = tmp_path / "out.zip"
        mock_converter_cls.return_value.convert.return_value = output

        result = convert_instance("input.xbrl", tmp_path, validate=True)

        assert result == output
        assert mock_validate.call_count == 2
        mock_converter_cls.return_value.convert.assert_called_once()

    @patch(_CONVERTER)
    @patch(_VALIDATE)
    def test_pre_validation_errors_stop_pipeline(
        self, mock_validate: MagicMock, mock_converter_cls: MagicMock
    ) -> None:
        """Pre-conversion errors raise ValidationError; no conversion attempted."""
        mock_validate.return_value = PRE_ERRORS

        with pytest.raises(ValidationError) as exc_info:
            convert_instance("input.xbrl", validate=True)

        assert exc_info.value.path is None
        assert exc_info.value.results is PRE_ERRORS
        mock_converter_cls.return_value.convert.assert_not_called()

    @patch(_CONVERTER)
    @patch(_VALIDATE)
    def test_post_validation_errors_have_path(
        self, mock_validate: MagicMock, mock_converter_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Post-conversion errors raise ValidationError with .path set."""
        output = tmp_path / "out.zip"
        mock_converter_cls.return_value.convert.return_value = output
        mock_validate.side_effect = [NO_ERRORS, POST_ERRORS]

        with pytest.raises(ValidationError) as exc_info:
            convert_instance("input.xbrl", tmp_path, validate=True)

        assert exc_info.value.path == output
        assert exc_info.value.results is POST_ERRORS

    @patch(_CONVERTER)
    @patch(_VALIDATE)
    def test_eba_flag_passed_through(
        self, mock_validate: MagicMock, mock_converter_cls: MagicMock, tmp_path: Path
    ) -> None:
        """eba=True is forwarded to both validate() calls."""
        mock_validate.return_value = NO_ERRORS
        output = tmp_path / "out.zip"
        mock_converter_cls.return_value.convert.return_value = output

        convert_instance("input.xbrl", tmp_path, validate=True, eba=True)

        pre_call, post_call = mock_validate.call_args_list
        assert pre_call.kwargs.get("eba") is True
        assert post_call.kwargs.get("eba") is True
        assert post_call.kwargs.get("post_conversion") is True


class TestPipelineValidateFalse:
    """Pipeline behaviour when validate=False (default)."""

    @patch(_CONVERTER)
    @patch(_VALIDATE)
    def test_no_validate_calls(
        self, mock_validate: MagicMock, mock_converter_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Default validate=False -> validate() is never called."""
        output = tmp_path / "out.zip"
        mock_converter_cls.return_value.convert.return_value = output

        result = convert_instance("input.xbrl", tmp_path)

        assert result == output
        mock_validate.assert_not_called()


class TestValidationErrorException:
    """Tests for the ValidationError exception itself."""

    def test_pre_conversion_message(self) -> None:
        ve = ValidationError(PRE_ERRORS)
        assert "Pre-conversion" in str(ve)
        assert "1 error(s)" in str(ve)
        assert ve.path is None

    def test_post_conversion_message(self) -> None:
        ve = ValidationError(POST_ERRORS, path=Path("out.zip"))
        assert "Post-conversion" in str(ve)
        assert ve.path == Path("out.zip")

    def test_results_attribute(self) -> None:
        ve = ValidationError(PRE_ERRORS)
        assert ve.results is PRE_ERRORS

    def test_is_value_error(self) -> None:
        assert issubclass(ValidationError, ValueError)
