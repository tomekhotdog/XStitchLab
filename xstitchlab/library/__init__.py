"""The design library: one DesignFolder per `designs/<slug>/`."""


class LibraryError(ValueError):
    """Bad slug, missing file, undecodable input, or unknown export kind."""


from xstitchlab.library.design_folder import DesignFolder, default_root  # noqa: E402

__all__ = ["DesignFolder", "LibraryError", "default_root"]
