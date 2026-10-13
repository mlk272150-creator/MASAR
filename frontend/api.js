(() => {
  const configured = window.localStorage.getItem("masar-api-base");
  const sameOriginApi = window.location.port === "8000";
  const defaultApi = sameOriginApi
    ? window.location.origin
    : `${window.location.protocol === "https:" ? "https:" : "http:"}//127.0.0.1:8000`;
  window.MasarApi = {
    baseUrl: (configured || defaultApi).replace(/\/+$/, ""),
    async request(path, options = {}) {
      let response;
      try {
        response = await fetch(`${this.baseUrl}${path}`, {
          ...options,
          headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
        });
      } catch (error) {
        throw new Error(`تعذّر الاتصال بالخادم: ${error.message}`);
      }
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = Array.isArray(payload.detail)
          ? payload.detail.map((item) => item.msg).join("، ")
          : payload.detail;
        throw new Error(detail || `خطأ من الخادم (${response.status})`);
      }
      return payload;
    },
    currentUser() {
      try {
        return JSON.parse(window.localStorage.getItem("masar-user") || "null");
      } catch {
        return null;
      }
    },
    requireUser() {
      const user = this.currentUser();
      if (!user?.id) {
        window.location.replace("./index.html");
        return null;
      }
      return user;
    },
    signOut() {
      window.localStorage.removeItem("masar-user");
      window.localStorage.removeItem("masar-token");
      window.location.replace("./index.html");
    },
    formatNumber(value) {
      return new Intl.NumberFormat("ar").format(value ?? 0);
    },
    escape(value) {
      return String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
      })[character]);
    },
  };
})();
