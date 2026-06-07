import React from "react";
import ReactDOM from "react-dom/client";
import { PermanentCharacterPage } from "./components/PermanentCharacterPage";
import { PermanentMonsterPage } from "./components/PermanentMonsterPage";
import { RulesLookupPage } from "./components/RulesLookupPage";
import { TabletopApp } from "./components/TabletopApp";
import "./styles/app.css";

const path = window.location.pathname;
const App = path.startsWith("/rules")
  ? RulesLookupPage
  : path.startsWith("/monsters")
    ? PermanentMonsterPage
  : path.startsWith("/characters/permanent")
    ? PermanentCharacterPage
    : TabletopApp;

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
