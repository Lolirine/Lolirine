# -*- coding: utf-8 -*-
import base64
import hashlib
import secrets
import time
from datetime import timedelta
from urllib.parse import urlparse

from odoo import api, fields, models, _
from odoo.exceptions import UserError


CLAUDE_REDIRECT_ALLOWLIST = (
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
)


class MerkagoMcpOauthClient(models.Model):
    _name = "merkago.mcp.oauth.client"
    _description = "MCP OAuth Client"
    _order = "id desc"

    name = fields.Char(required=True)
    client_id = fields.Char(required=True, index=True, copy=False)
    client_secret_hash = fields.Char(copy=False)
    client_secret_prefix = fields.Char(readonly=True, copy=False)
    redirect_uris = fields.Text(
        required=True,
        default="\n".join(CLAUDE_REDIRECT_ALLOWLIST),
        help="One redirect URI per line.",
    )
    grant_types = fields.Char(default="authorization_code,refresh_token")
    token_endpoint_auth_method = fields.Char(default="none")
    active = fields.Boolean(default=True)
    dynamic = fields.Boolean(
        string="Dynamically Registered",
        default=False,
        help="Created via RFC 7591 Dynamic Client Registration.",
    )

    # Odoo 19 : _sql_constraints n'est plus pris en compte
    _client_id_uniq = models.Constraint("UNIQUE (client_id)", "Client ID must be unique.")

    @api.model
    def _hash_secret(self, secret):
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    @api.model
    def _generate_client_id(self):
        return "mcp_cli_%s" % secrets.token_urlsafe(16)

    @api.model
    def _generate_client_secret(self):
        return "mcp_sec_%s" % secrets.token_urlsafe(24)

    def _redirect_uri_list(self):
        self.ensure_one()
        return [u.strip() for u in (self.redirect_uris or "").splitlines() if u.strip()]

    @api.model
    def _redirect_uri_is_trusted(self, redirect_uri):
        """[Lolirine] Seules les adresses de retour de Claude (claude.ai / claude.com)
        et localhost (Claude Code, Claude Desktop) sont acceptées. Empêche un tiers
        d'enregistrer un client renvoyant le code d'autorisation vers son serveur."""
        if not redirect_uri:
            return False
        if redirect_uri in CLAUDE_REDIRECT_ALLOWLIST:
            return True
        parsed = urlparse(redirect_uri)
        if parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost"):
            return True
        return False

    def _redirect_allowed(self, redirect_uri):
        self.ensure_one()
        if not self._redirect_uri_is_trusted(redirect_uri):
            return False
        if redirect_uri in CLAUDE_REDIRECT_ALLOWLIST:
            return True
        return redirect_uri in self._redirect_uri_list()

    def check_secret(self, secret):
        self.ensure_one()
        if not self.client_secret_hash:
            return True  # public client (PKCE)
        if not secret:
            return False
        return self.client_secret_hash == self._hash_secret(secret)

    @api.model
    def register_dynamic(self, payload):
        """RFC 7591 Dynamic Client Registration."""
        redirect_uris = payload.get("redirect_uris") or list(CLAUDE_REDIRECT_ALLOWLIST)
        if isinstance(redirect_uris, str):
            redirect_uris = [redirect_uris]
        untrusted = [u for u in redirect_uris if not self._redirect_uri_is_trusted(u)]
        if untrusted:
            raise UserError(_("redirect_uri not allowed: %s") % ", ".join(map(str, untrusted)))
        name = payload.get("client_name") or "Claude Desktop"
        auth_method = payload.get("token_endpoint_auth_method") or "none"
        client_id = self._generate_client_id()
        vals = {
            "name": name,
            "client_id": client_id,
            "redirect_uris": "\n".join(redirect_uris),
            "grant_types": ",".join(payload.get("grant_types") or ["authorization_code", "refresh_token"]),
            "token_endpoint_auth_method": auth_method,
            "dynamic": True,
        }
        raw_secret = None
        if auth_method not in ("none",):
            raw_secret = self._generate_client_secret()
            vals["client_secret_hash"] = self._hash_secret(raw_secret)
            vals["client_secret_prefix"] = raw_secret[:12]
        client = self.sudo().create(vals)
        result = {
            "client_id": client.client_id,
            "client_name": client.name,
            "redirect_uris": redirect_uris,
            "grant_types": [g.strip() for g in client.grant_types.split(",") if g.strip()],
            "response_types": ["code"],
            "token_endpoint_auth_method": auth_method,
            "client_id_issued_at": int(time.time()),
        }
        if raw_secret:
            result["client_secret"] = raw_secret
        return result


class MerkagoMcpOauthCode(models.Model):
    _name = "merkago.mcp.oauth.code"
    _description = "MCP OAuth Authorization Code"
    _order = "id desc"

    code = fields.Char(required=True, index=True)
    client_id = fields.Many2one("merkago.mcp.oauth.client", required=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    redirect_uri = fields.Char(required=True)
    code_challenge = fields.Char(required=True)
    code_challenge_method = fields.Char(default="S256")
    scope = fields.Char(default="mcp")
    expires_at = fields.Datetime(required=True)
    used = fields.Boolean(default=False)

    @api.model
    def create_code(self, client, user, redirect_uri, code_challenge, method="S256", scope="mcp"):
        raw = secrets.token_urlsafe(32)
        rec = self.sudo().create(
            {
                "code": raw,
                "client_id": client.id,
                "user_id": user.id,
                "redirect_uri": redirect_uri,
                "code_challenge": code_challenge,
                "code_challenge_method": method or "S256",
                "scope": scope or "mcp",
                "expires_at": fields.Datetime.now() + timedelta(minutes=10),
            }
        )
        return raw, rec

    def consume(self, code_verifier, redirect_uri):
        self.ensure_one()
        if self.used:
            raise UserError(_("Authorization code already used."))
        if self.expires_at < fields.Datetime.now():
            raise UserError(_("Authorization code expired."))
        if redirect_uri and redirect_uri != self.redirect_uri:
            raise UserError(_("redirect_uri mismatch."))
        # [Lolirine] code marqué utilisé AVANT la vérification : un code n'est
        # jamais rejouable, même après un échec PKCE.
        self.sudo().write({"used": True})
        if self.code_challenge_method != "S256":
            raise UserError(_("Unsupported code_challenge_method."))
        digest = hashlib.sha256((code_verifier or "").encode("ascii")).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        if not secrets.compare_digest(computed, self.code_challenge or ""):
            raise UserError(_("PKCE verification failed."))
        return True


class MerkagoMcpOauthAccess(models.Model):
    _name = "merkago.mcp.oauth.access"
    _description = "MCP OAuth Access Token"
    _order = "id desc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    client_id = fields.Many2one("merkago.mcp.oauth.client", required=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    token_prefix = fields.Char(readonly=True)
    token_hash = fields.Char(required=True, index=True)
    refresh_hash = fields.Char(index=True)
    scope = fields.Char(default="mcp")
    expires_at = fields.Datetime(required=True)
    mcp_token_id = fields.Many2one("merkago.mcp.token", ondelete="set null")

    @api.model
    def _hash(self, raw):
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @api.model
    def issue(self, client, user, scope="mcp", hours=24, previous=None):
        """Émet un access token + refresh token.

        [Lolirine] Lors d'un renouvellement (``previous`` = ancien accès), les réglages
        du token précédent (scopes, Safe Mode forcé, sociétés, quota) sont conservés
        au lieu de repartir sur "tous les scopes actifs".
        """
        access_raw = "mcp_at_%s" % secrets.token_urlsafe(32)
        refresh_raw = "mcp_rt_%s" % secrets.token_urlsafe(32)
        Token = self.env["merkago.mcp.token"].sudo()
        prev_token = previous.mcp_token_id if previous else Token.browse()
        vals = {
            "name": _("OAuth — %s") % (client.name or "Claude"),
            "user_id": user.id,
            "token_prefix": access_raw[:12],
            "token_hash": Token._hash_token(access_raw),
        }
        if prev_token:
            vals.update(
                {
                    "name": prev_token.name,
                    "safe_mode": prev_token.safe_mode,
                    "daily_quota": prev_token.daily_quota,
                    "scope_ids": [(6, 0, prev_token.scope_ids.ids)],
                    "company_ids": [(6, 0, prev_token.company_ids.ids)],
                }
            )
        else:
            # nouvelle connexion : tous les scopes actifs (le contrôle se fait en
            # activant / archivant les scopes dans Merkago MCP → Scopes)
            scopes = self.env["merkago.mcp.scope"].sudo().search([("active", "=", True)])
            vals["scope_ids"] = [(6, 0, scopes.ids)]
        mcp_token = Token.create(vals)
        rec = self.sudo().create(
            {
                "name": mcp_token.name,
                "client_id": client.id,
                "user_id": user.id,
                "token_prefix": access_raw[:12],
                "token_hash": self._hash(access_raw),
                "refresh_hash": self._hash(refresh_raw),
                "scope": scope or "mcp",
                "expires_at": fields.Datetime.now() + timedelta(hours=hours),
                "mcp_token_id": mcp_token.id,
            }
        )
        return {
            "access_token": access_raw,
            "refresh_token": refresh_raw,
            "token_type": "Bearer",
            "expires_in": hours * 3600,
            "scope": scope or "mcp",
            "record": rec,
        }

    @api.model
    def authenticate(self, raw_token):
        if not raw_token:
            return self.browse()
        raw_token = raw_token.strip()
        if raw_token.lower().startswith("bearer "):
            raw_token = raw_token[7:].strip()
        rec = self.sudo().search(
            [("token_hash", "=", self._hash(raw_token)), ("active", "=", True)],
            limit=1,
        )
        if not rec:
            return self.browse()
        if rec.expires_at and rec.expires_at < fields.Datetime.now():
            return self.browse()
        return rec

    def refresh(self, refresh_raw):
        self.ensure_one()
        if not secrets.compare_digest(self.refresh_hash or "", self._hash(refresh_raw or "")):
            raise UserError(_("Invalid refresh token."))
        user = self.user_id
        if not user.active or user.share or user._is_system() or not user.has_group(
            "merkago_mcp_server.group_mcp_user"
        ):
            raise UserError(_("User no longer allowed to use MCP."))
        if self.mcp_token_id and not self.mcp_token_id.active:
            raise UserError(_("Access revoked."))
        # [Lolirine] rotation réelle : l'ancien access token, son refresh token
        # et le token MCP associé sont révoqués.
        issued = self.issue(self.client_id, user, scope=self.scope, previous=self)
        self.sudo().write({"active": False})
        if self.mcp_token_id:
            self.mcp_token_id.sudo().write({"active": False})
        return issued
