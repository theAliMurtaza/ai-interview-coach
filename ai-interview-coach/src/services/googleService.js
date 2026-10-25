let loading;
const SCRIPT_URL = "https://accounts.google.com/gsi/client";

export function loadGoogleIdentity() {
  if (window.google?.accounts?.id) return Promise.resolve(window.google.accounts.id);
  if (!loading) {
    loading = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = SCRIPT_URL;
      script.async = true;
      const timeout = setTimeout(() => fail(), 15000);
      function fail() {
        clearTimeout(timeout);
        script.remove();
        reject(new Error("Google sign-in could not load. Retry or use email and password."));
      }
      script.onerror = fail;
      script.onload = () => {
        clearTimeout(timeout);
        if (!window.google?.accounts?.id) { fail(); return; }
        resolve(window.google.accounts.id);
      };
      document.head.appendChild(script);
    }).catch(error => { loading = null; throw error; });
  }
  return loading;
}
