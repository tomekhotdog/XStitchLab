"""Map library and op errors to HTTP responses.

OpParamError (bad op params) -> 422 with the pydantic errors as `detail`;
any other OpError -> 400 `{detail, step_index, op}`; LibraryError -> 400;
a bare ValidationError -> 422.
"""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from xstitchlab.library import LibraryError
from xstitchlab.ops.base import OpError, OpParamError


def install(app: FastAPI) -> None:
    @app.exception_handler(OpError)
    async def op_error(request: Request, exc: OpError) -> JSONResponse:
        if isinstance(exc, OpParamError):
            return JSONResponse(
                status_code=422,
                content={"detail": jsonable_encoder(exc.errors), "step_index": exc.step_index, "op": exc.op},
            )
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "step_index": exc.step_index, "op": exc.op},
        )

    @app.exception_handler(LibraryError)
    async def library_error(request: Request, exc: LibraryError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors(include_url=False))})
