from __future__ import annotations

from hashlib import sha256

import keyring
from keyring.errors import KeyringError

from agentsystem.domain import CredentialCreate, CredentialMetadataRecord
from agentsystem.store import InMemoryStore


class CredentialBackendError(RuntimeError):
    pass


class CredentialService:
    SERVICE_NAME = "AgentSystem"

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def create(self, payload: CredentialCreate) -> CredentialMetadataRecord:
        fingerprint = sha256(payload.secret.encode("utf-8")).hexdigest()[:12]
        metadata = CredentialMetadataRecord(name=payload.name, fingerprint=fingerprint)
        try:
            keyring.set_password(self.SERVICE_NAME, metadata.id, payload.secret)
        except KeyringError as exc:
            raise CredentialBackendError("macOS Keychain is unavailable") from exc
        return self.store.add_credential(metadata)

    def list(self) -> list[CredentialMetadataRecord]:
        return self.store.list_credentials()

    def exists(self, credential_id: str) -> bool:
        metadata = self.store.get_credential(credential_id)
        try:
            available = keyring.get_password(self.SERVICE_NAME, credential_id) is not None
        except KeyringError:
            available = False
        return available

    def resolve(self, credential_id: str) -> str:
        self.store.get_credential(credential_id)
        try:
            secret = keyring.get_password(self.SERVICE_NAME, credential_id)
        except KeyringError as exc:
            raise CredentialBackendError("macOS Keychain is unavailable") from exc
        if secret is None:
            raise CredentialBackendError("Credential is missing from macOS Keychain")
        return secret

    def delete(self, credential_id: str) -> CredentialMetadataRecord:
        metadata = self.store.get_credential(credential_id)
        try:
            keyring.delete_password(self.SERVICE_NAME, credential_id)
        except keyring.errors.PasswordDeleteError:
            pass
        except KeyringError as exc:
            raise CredentialBackendError("macOS Keychain is unavailable") from exc
        self.store.delete_credential(credential_id)
        return metadata
