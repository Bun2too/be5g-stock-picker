import React from "react";
import ReactDOM from "react-dom/client";
import { Auth0Provider } from "@auth0/auth0-react";
import App from "./App";
import "./styles.css";

const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN;
const auth0ClientId = import.meta.env.VITE_AUTH0_CLIENT_ID;
const auth0Audience = import.meta.env.VITE_AUTH0_AUDIENCE;
const auth0RedirectUri = import.meta.env.VITE_AUTH0_REDIRECT_URI || window.location.origin;

const app = auth0Domain && auth0ClientId ? (
  <Auth0Provider
    domain={auth0Domain}
    clientId={auth0ClientId}
    authorizationParams={{
      redirect_uri: auth0RedirectUri,
      ...(auth0Audience ? { audience: auth0Audience } : {}),
    }}
  >
    <App authEnabled />
  </Auth0Provider>
) : (
  <App authEnabled={false} />
);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {app}
  </React.StrictMode>
);
