import logging
import os
from datetime import date, datetime
from pathlib import Path, PosixPath
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
from orchestration.prefect.exceptions import MissingSourceCredentialsError
from orchestration.prefect.utils import get_credentials
from prefect import get_run_logger, task

from viadot.sources import Mindful

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@task(retries=3, retry_delay_seconds=10, timeout_seconds=60 * 60)
def mindful_to_df(
    credentials: Optional[Dict[str, Any]] = None,
    config_key: str = "mindful",
    azure_key_vault_secret: Optional[str] = None,
    region: Literal["us1", "us2", "us3", "ca1", "eu1", "au1"] = "eu1",
    endpoint: Optional[str] = None,
    date_interval: Optional[List[date]] = None,
    limit: int = 1000,
) -> pd.DataFrame:
    """
    Description:
        Task for downloading data from Mindful API to CSV

    Args:
        credentials (Optional[Dict[str, Any]], optional): Mindful credentials as a dictionary.
            Defaults to None.
        config_key (str, optional): The key in the viadot config holding relevant credentials.
            Defaults to "mindful".
        azure_key_vault_secret (Optional[str], optional): The name of the Azure Key Vault secret
            where credentials are stored. Defaults to None.
        region (Literal[us1, us2, us3, ca1, eu1, au1], optional): Survey Dynamix region from
            where to interact with the mindful API. Defaults to "eu1" English (United Kingdom).
        endpoint (Optional[str], optional): API endpoint for an individual request. Defaults to None.
        date_interval (Optional[List[date]], optional): Date time range detailing the starting date and the ending date.
            If no range is passed, one day of data since this moment will be retrieved. Defaults to None.
        limit (int, optional): The number of matching interactions to return. Defaults to 1000.

    Returns:
        pd.DataFrame: The response data as a Pandas Data Frame.
    """

    logger = get_run_logger()

    if not (azure_key_vault_secret or config_key or credentials):
        raise MissingSourceCredentialsError
    credentials = credentials or get_credentials(azure_key_vault_secret)

    if endpoint is None:
        logger.warning(
            "The API endpoint parameter was not defined. The default value is 'surveys'."
        )
        endpoint = "surveys"

    mindful = Mindful(
        credentials=credentials,
        config_key=config_key,
        region=region,
    )
    mindful.api_connection(
        endpoint=endpoint,
        date_interval=date_interval,
        limit=limit,
    )
    data_frame = mindful.to_df()

    return data_frame


@task(retries=3, retry_delay_seconds=10, timeout_seconds=60 * 60)
def mindful_to_file(
    data_frame: pd.DataFrame,
    path: Optional[str] = None,
    sep: str = "\t",
) -> PosixPath:
    """
    Description:
        Save mindful Data Frame to a local path.

    Args:
        data_frame (pd.DataFrame):
        path (str, optional): Absolute or relative path, with name, to save
            the Pandas Data Frame. Defaults to None.
        sep (str, optional): Separator in csv file. Defaults to "\t".

    Raises:
        ValueError: Not available file extension.

    Returns:
        PosixPath: Local path where the file has been saved.
    """

    logger = get_run_logger()

    if path is None:
        path = Path(
            os.path.join(
                os.getcwd(),
                f"mindful_response_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
            )
        )
    else:
        path = Path(path).absolute()

    if os.path.exists(path.parent) is False:
        path.parent.mkdir(parents=True)

    if path.suffix == ".csv":
        data_frame.to_csv(path, index=False, sep=sep)
    elif path.suffix == ".parquet":
        data_frame.to_parquet(path, index=False)
    else:
        raise ValueError("File extension must be either 'csv' or 'parquet'.")

    logger.info(f"The file was saved correctly at {path}")

    return path
