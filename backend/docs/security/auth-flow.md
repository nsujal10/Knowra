



# Authentication Flows

## Registration & Organization Onboarding
```text
Client -> POST /register (User Data, Org Name)
API -> Create Organization
API -> Create User
API -> Create Membership (User, Org, Role=ADMIN)
API -> Return User & Org
```

## Token Refresh & Breach Detection
```text
Client -> POST /refresh (Refresh Token)
API -> Hash Token -> Lookup Session
alt Valid & Active
    API -> Revoke old session, issue new Refresh + Access Tokens
    API -> Return Tokens
else Already Revoked
    API -> BREACH DETECTED
    API -> Revoke all active sessions for User
    API -> Log Security Audit Event
    API -> Return 401 Unauthorized
end
```
