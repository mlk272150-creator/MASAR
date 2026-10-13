const pricingUser = MasarApi.requireUser();
const pricingToast = document.querySelector("#toast");
let pricingToastTimer;

function showPricingMessage(message, isError = false) {
  pricingToast.textContent = message;
  pricingToast.classList.toggle("error", isError);
  pricingToast.classList.add("visible");
  window.clearTimeout(pricingToastTimer);
  pricingToastTimer = window.setTimeout(() => pricingToast.classList.remove("visible"), 3500);
}

function initializePricing() {
  const name = pricingUser.username || pricingUser.phone_number || "م";
  document.querySelector("#user-name").textContent = name;
  document.querySelector("#user-avatar").textContent = [...name][0] || "م";
  document.querySelector("#logout-button").addEventListener("click", () => MasarApi.signOut());
  document.querySelector("#pricing-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.innerHTML = "جارٍ احتساب التقدير…";
    try {
      const result = await MasarApi.request("/ai/pricing/estimate", {
        method: "POST",
        body: JSON.stringify({
          requested_task: {
            region: values.get("region").trim(),
            profession: values.get("profession").trim(),
            demand: Number(values.get("demand")),
            supply: Number(values.get("supply")),
          },
        }),
      });
      document.querySelector("#price-value").textContent = MasarApi.formatNumber(result.predicted_price_points);
      document.querySelector("#price-message").textContent = `استند التقدير إلى ${MasarApi.formatNumber(result.training_examples)} سجل اصطناعي؛ لا تمثل النتيجة سعراً سوقياً موثقاً.`;
      showPricingMessage("اكتمل تقدير سعر المهمة.");
    } catch (error) {
      showPricingMessage(error.message, true);
    } finally {
      button.disabled = false;
      button.innerHTML = 'احسب السعر المقترح <span>✳</span>';
    }
  });
}

initializePricing();
