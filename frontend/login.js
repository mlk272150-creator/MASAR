const loginForm = document.querySelector("#login-form");
const loginButton = loginForm.querySelector("button[type=submit]");
const loginMessage = document.querySelector("#login-message");

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginMessage.textContent = "";
  loginButton.disabled = true;
  loginButton.innerHTML = "جارٍ التحقق…";
  const values = new FormData(loginForm);
  try {
    const result = await MasarApi.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        phone_number: values.get("phone_number").trim(),
        password: values.get("password"),
      }),
    });
    window.localStorage.setItem("masar-user", JSON.stringify(result.user));
    window.localStorage.setItem("masar-token", result.token);
    window.location.assign("./dashboard.html");
  } catch (error) {
    loginMessage.textContent = error.message;
  } finally {
    loginButton.disabled = false;
    loginButton.innerHTML = 'تسجيل الدخول <span aria-hidden="true">←</span>';
  }
});
