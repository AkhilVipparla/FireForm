import os
from datetime import datetime

from app.core.logging import get_logger
from app.services.form_filler import filler

logger = get_logger(__name__)


class FileManipulator:

    def prepare_fillable(self, pdf_path: str):
        """
        Run commonforms on a flat PDF to detect form regions and produce a
        fillable PDF. Returns the new path (alongside the original).
        """
        # Disable CUDA to force CPU usage, preventing errors on Mac Silicon / Docker
        import os
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

        # Monkey patch rfdetr to force CPU usage on Mac Silicon / Docker
        try:
            import rfdetr.detr
            original_ensure = rfdetr.detr._ensure_model_on_device
            def patched_ensure(model_ctx):
                model_ctx.device = "cpu"
                original_ensure(model_ctx)
            rfdetr.detr._ensure_model_on_device = patched_ensure
        except ImportError:
            pass

        from commonforms import prepare_form
        template_path = pdf_path[:-4] + "_template.pdf"

        prepare_form(pdf_path, template_path)
        return template_path

    def fill_form(self, user_input: str, fields: list, pdf_form_path: str, model: str = None):
        """
        It receives the raw data, runs the PDF filling logic,
        and returns the path to the newly created file.

        `fields` is unused: form_filler reads the fields, tables and tooltip
        descriptions straight from the PDF.
        """
        logger.info("[1] Received request from frontend.")
        logger.info("[2] PDF template path: %s", pdf_form_path)

        actual_pdf_path = pdf_form_path
        try:
            resolved_pdf = paths._resolve_project_file(pdf_form_path)
            if resolved_pdf.exists():
                actual_pdf_path = str(resolved_pdf)
        except Exception:
            actual_pdf_path = pdf_form_path

        if not os.path.exists(actual_pdf_path):
            raise FileNotFoundError(f"PDF template not found at {pdf_form_path}")

        logger.info("[3] Starting extraction and PDF filling process...")
        try:
            output_name = (
                actual_pdf_path[:-4]
                + "_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
                + "_filled.pdf"
            )
            filler.fill(actual_pdf_path, user_input, output_name, model)

            logger.info("Process complete. Output saved to: %s", output_name)

            try:
                from pathlib import Path
                return Path(output_name).relative_to(paths.PROJECT_ROOT).as_posix()
            except Exception:
                return output_name

        except Exception as e:
            logger.error("An error occurred during PDF generation: %s", e)
            raise e
