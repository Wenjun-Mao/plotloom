import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./selection-controls.css";
import "./creator-ui.css";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
