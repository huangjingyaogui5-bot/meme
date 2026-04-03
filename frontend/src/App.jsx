// frontend/src/App.jsx
import { useState } from "react"
import UploadPage from "./pages/UploadPage"
import AnalysisPage from "./pages/AnalysisPage"

export default function App() {
  const [session, setSession] = useState(null)

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0A0E1A",
      color: "#E8EEF8",
      fontFamily: "monospace"
    }}>
      {!session
        ? <UploadPage onSessionReady={setSession} />
        : <AnalysisPage session={session} onReset={() => setSession(null)} />
      }
    </div>
  )
}
