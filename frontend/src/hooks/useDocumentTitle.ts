import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const SITE_NAME = "DeepLV Translator";

/** Sets the tab title and canonical link for the current route. */
export function useDocumentTitle(title: string) {
  const location = useLocation();

  useEffect(() => {
    document.title = title === SITE_NAME ? title : `${title} | ${SITE_NAME}`;

    let canonical = document.querySelector<HTMLLinkElement>("link[rel='canonical']");
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.rel = "canonical";
      document.head.appendChild(canonical);
    }
    canonical.href = `${window.location.origin}${location.pathname}`;
  }, [title, location.pathname]);
}
