from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query
from sqlmodel import Session

from app.database import get_session
from app.service.client_exceptions import (
    ClientHasOrdersError,
    ClientNotFoundByEmailError,
    ClientNotFoundByIdError,
    ClientNotFoundForUpdate,
    DuplicateClientEmailError,
)
from app.service.order_exceptions import (
    InsufficientProductStockError,
    OrderCancelledError,
    OrderNotFoundError,
    OrderProductNotFoundError,
)
from app.service.order_exceptions import (
    ProductNotFoundError as OrderProductMissingError,
)
from app.service.message_exceptions import (
    EmailNotConfiguredError,
    MailServerError,
    NoRecipientsError,
)
from app.service.product_exceptions import ProductInUseError, ProductNotFoundError

SessionDep = Annotated[Session, Depends(get_session)]
PositiveId = Annotated[int, Path(gt=0)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


@contextmanager
def service_errors():
    """Translate expected service failures without hiding unexpected errors."""
    try:
        yield
    except (
        ClientNotFoundByEmailError,
        ClientNotFoundByIdError,
        ClientNotFoundForUpdate,
        OrderNotFoundError,
        OrderProductNotFoundError,
        OrderProductMissingError,
        ProductNotFoundError,
    ) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        DuplicateClientEmailError,
        ClientHasOrdersError,
        ProductInUseError,
        InsufficientProductStockError,
        OrderCancelledError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (EmailNotConfiguredError, MailServerError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NoRecipientsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
