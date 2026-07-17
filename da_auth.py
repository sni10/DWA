"""
DeviantArt OAuth2 authentication module for ComfyUI node.

Handles:
- Token storage in SQLite database
- OAuth2 authorization flow via browser
- Token validation using GET /placebo
- Token refresh when expired
"""

import json
import sqlite3
import threading
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

# API URLs
API_BASE_URL = "https://www.deviantart.com"
OAUTH_AUTHORIZE_URL = f"{API_BASE_URL}/oauth2/authorize"
OAUTH_TOKEN_URL = f"{API_BASE_URL}/oauth2/token"
API_PLACEBO_URL = f"{API_BASE_URL}/api/v1/oauth2/placebo"


class TokenStorage:
    """SQLite-based token storage for standalone operation."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize token storage.

        Args:
            db_path: Path to SQLite database file. Defaults to
                     'da_tokens.db' in the same directory as this module.
        """
        if db_path is None:
            db_path = str(Path(__file__).parent / "da_tokens.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                id INTEGER PRIMARY KEY,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def save_token(self, token_data: dict) -> None:
        """
        Save token data to database.

        Args:
            token_data: Dictionary with access_token, refresh_token, expires_in
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate expiration time
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Delete old tokens
        cursor.execute("DELETE FROM oauth_tokens")

        # Insert new token
        cursor.execute(
            """
            INSERT INTO oauth_tokens (access_token, refresh_token, expires_at)
            VALUES (?, ?, ?)
            """,
            (
                token_data.get("access_token"),
                token_data.get("refresh_token"),
                expires_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_token(self) -> Optional[dict]:
        """
        Get stored token data.

        Returns:
            Token dictionary or None if not found.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT access_token, refresh_token, expires_at FROM oauth_tokens LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "access_token": row[0],
                "refresh_token": row[1],
                "expires_at": row[2],
            }
        return None

    def delete_token(self) -> None:
        """Delete stored token."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM oauth_tokens")
        conn.commit()
        conn.close()

    def is_token_expired(self) -> bool:
        """
        Check if stored token is expired.

        Returns:
            True if token is expired or not found.
        """
        token = self.get_token()
        if not token or not token.get("expires_at"):
            return True

        expires_at = datetime.fromisoformat(token["expires_at"])
        # Add 5 minute buffer
        return datetime.now() >= (expires_at - timedelta(minutes=5))


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth callback."""

    authorization_code: Optional[str] = None

    def do_GET(self) -> None:
        """Handle GET request from OAuth callback."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.authorization_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            response = """
            <html>
            <body>
            <h1>Authorization Successful!</h1>
            <p>You can close this window and return to ComfyUI.</p>
            <script>window.close();</script>
            </body>
            </html>
            """
            self.wfile.write(response.encode())
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            error = params.get("error", ["Unknown error"])[0]
            self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())

    def log_message(self, format: str, *args) -> None:
        """Suppress HTTP server logging."""
        pass


class DeviantArtAuth:
    """DeviantArt OAuth2 authentication handler."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8080/callback/",
        scopes: str = "browse stash publish",
        db_path: Optional[str] = None,
    ):
        """
        Initialize authentication handler.

        Args:
            client_id: DeviantArt application client ID
            client_secret: DeviantArt application client secret
            redirect_uri: OAuth redirect URI (default: http://localhost:8080/callback)
            scopes: OAuth scopes (default: browse stash publish)
            db_path: Path to token database file
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.storage = TokenStorage(db_path)

    def validate_token(self, access_token: str) -> bool:
        """
        Validate access token using placebo endpoint.

        Args:
            access_token: Token to validate

        Returns:
            True if token is valid, False otherwise.
        """
        try:
            response = requests.get(
                API_PLACEBO_URL,
                params={"access_token": access_token},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("status") == "success"
        except requests.RequestException:
            return False

    def authorize(self) -> bool:
        """
        Perform OAuth2 authorization flow via browser.

        Opens browser for user authorization and waits for callback.

        Returns:
            True if authorization successful, False otherwise.
        """
        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
        }
        auth_url = f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

        # Parse redirect URI to get host and port
        parsed = urlparse(self.redirect_uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080

        # Reset authorization code
        OAuthCallbackHandler.authorization_code = None

        # Start callback server in background thread
        server = HTTPServer((host, port), OAuthCallbackHandler)
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.daemon = True
        server_thread.start()

        # Open browser for authorization
        print(f"Opening browser for DeviantArt authorization...")
        webbrowser.open(auth_url)

        # Wait for callback (timeout after 120 seconds)
        server_thread.join(timeout=120)
        server.server_close()

        if not OAuthCallbackHandler.authorization_code:
            print("Authorization failed: No code received")
            return False

        # Exchange code for token
        return self._exchange_code(OAuthCallbackHandler.authorization_code)

    def _exchange_code(self, code: str) -> bool:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from callback

        Returns:
            True if exchange successful, False otherwise.
        """
        try:
            response = requests.post(
                OAUTH_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                },
                timeout=30,
            )
            response.raise_for_status()
            token_data = response.json()

            if token_data.get("status") == "success" or "access_token" in token_data:
                self.storage.save_token(token_data)
                print("Authorization successful! Token saved.")
                return True

            print(f"Token exchange failed: {token_data.get('error_description', 'Unknown error')}")
            return False

        except requests.RequestException as e:
            print(f"Token exchange error: {e}")
            return False

    def refresh_token(self) -> bool:
        """
        Refresh access token using stored refresh token.

        Returns:
            True if refresh successful, False otherwise.
        """
        token = self.storage.get_token()
        if not token or not token.get("refresh_token"):
            return False

        try:
            response = requests.post(
                OAUTH_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": token["refresh_token"],
                },
                timeout=30,
            )
            response.raise_for_status()
            token_data = response.json()

            if token_data.get("status") == "success" or "access_token" in token_data:
                self.storage.save_token(token_data)
                return True

            return False

        except requests.RequestException:
            return False

    def get_valid_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing or re-authorizing if needed.

        Returns:
            Valid access token or None if authentication fails.
        """
        token = self.storage.get_token()

        # If we have a token, validate it with placebo
        if token and token.get("access_token"):
            if self.validate_token(token["access_token"]):
                return token["access_token"]

            # Token invalid, try refresh
            print("Token expired or invalid, attempting refresh...")
            if self.refresh_token():
                token = self.storage.get_token()
                if token:
                    return token["access_token"]

        # No valid token, delete old and re-authorize
        print("No valid token found, need to re-authorize...")
        self.storage.delete_token()
        if self.authorize():
            token = self.storage.get_token()
            if token:
                return token["access_token"]

        return None

    def ensure_authenticated(self) -> Optional[str]:
        """
        Ensure we have valid authentication.

        This is the main entry point for the node to get a valid token.
        It will validate existing token with placebo, refresh if needed,
        or trigger full re-authorization via browser.

        Returns:
            Valid access token or None if authentication fails.
        """
        return self.get_valid_token()
