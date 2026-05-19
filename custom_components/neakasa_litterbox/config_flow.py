"""Config flow for neakasa_litterbox."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .api import NeakasaApiClient
from .const import CONF_REGION, DEFAULT_REGION, DOMAIN, LOGGER, REGIONS
from .exceptions import (
    NeakasaApiClientAuthenticationError,
    NeakasaApiClientCommunicationError,
    NeakasaApiClientError,
)
from .options_flow import NeakasaOptionsFlow

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .data import NeakasaConfigData, NeakasaConfigEntry


def _credentials_schema(
    default_username: str | None = None,
    default_region: str = DEFAULT_REGION,
) -> vol.Schema:
    """Build the email/password/region schema, optionally pre-filled."""
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME,
                default=default_username
                if default_username is not None
                else vol.UNDEFINED,
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL),
            ),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
            ),
            vol.Required(
                CONF_REGION,
                default=default_region,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(REGIONS),
                    translation_key=CONF_REGION,
                ),
            ),
        },
    )


class NeakasaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Neakasa Litterbox."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: NeakasaConfigEntry,  # noqa: ARG004
    ) -> NeakasaOptionsFlow:
        """Return the options flow handler."""
        return NeakasaOptionsFlow()

    # ``NeakasaConfigData`` narrows HA's base ``dict[str, Any] | None`` to our
    # own schema. The trade-off is a deliberate LSP violation.
    async def async_step_user(  # type: ignore[override]
        self,
        user_input: NeakasaConfigData | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._validate(user_input)
            if not errors:
                await self.async_set_unique_id(slugify(user_input["username"]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input["username"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_credentials_schema(
                default_username=user_input["username"] if user_input else None,
                default_region=(user_input["region"] if user_input else DEFAULT_REGION),
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, str],  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Trigger reauth when the API rejects stored credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: NeakasaConfigData | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Prompt the user for new credentials and update the entry."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        existing = cast("NeakasaConfigData", entry.data)

        if user_input is not None:
            errors = await self._validate(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=dict(user_input),
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_credentials_schema(
                default_username=existing.get("username"),
                default_region=existing.get("region", DEFAULT_REGION),
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: NeakasaConfigData | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Allow editing credentials of an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        existing = cast("NeakasaConfigData", entry.data)

        if user_input is not None:
            errors = await self._validate(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=dict(user_input),
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_credentials_schema(
                default_username=existing.get("username"),
                default_region=existing.get("region", DEFAULT_REGION),
            ),
            errors=errors,
        )

    async def _validate(self, user_input: NeakasaConfigData) -> dict[str, str]:
        """Test credentials and return an errors dict (empty on success)."""
        try:
            await self._test_credentials(
                username=user_input["username"],
                password=user_input["password"],
                region=user_input["region"],
            )
        except NeakasaApiClientAuthenticationError as exception:
            LOGGER.warning("Auth error during credential validation: %s", exception)
            return {"base": "auth"}
        except NeakasaApiClientCommunicationError as exception:
            LOGGER.error("Connection error during credential validation: %s", exception)
            return {"base": "connection"}
        except NeakasaApiClientError:
            LOGGER.exception("Unexpected error during credential validation")
            return {"base": "unknown"}
        return {}

    async def _test_credentials(
        self,
        username: str,
        password: str,
        region: str,
    ) -> None:
        """Validate credentials against the Neakasa cloud."""
        client = NeakasaApiClient(
            username=username,
            password=password,
            region=region,
        )
        try:
            await client.async_login()
        finally:
            await client.async_close()
