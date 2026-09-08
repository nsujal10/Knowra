from abc import ABC, abstractmethod

class IdentityProvider(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str):
        pass

class LocalIdentityProvider(IdentityProvider):
    def authenticate(self, username: str, password: str):
        pass
