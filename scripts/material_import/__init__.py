"""Examiner ZIP import: inspection, redaction, text extraction, storage and upload.

``scripts/import-material.py`` is the command-line entry point. These modules import
only the standard library; PDF parsing loads the backend's pypdf in a bounded subprocess.
"""
