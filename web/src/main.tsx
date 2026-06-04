import React from "react";
import ReactDOM from "react-dom/client";
import { TabletopApp } from "./components/TabletopApp";
import "./styles/app.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <TabletopApp />
  </React.StrictMode>
);
