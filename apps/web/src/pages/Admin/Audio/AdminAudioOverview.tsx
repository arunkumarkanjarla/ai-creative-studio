import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function AdminAudioOverview() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate("/admin/audio-activity", { replace: true });
  }, [navigate]);

  return null;
}
