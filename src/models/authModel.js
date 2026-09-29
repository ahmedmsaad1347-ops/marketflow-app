export const AuthModel = {
  login(email, password) {
    if (!email || !password) {
      return { success: false, message: "Enter email and password" };
    }

    localStorage.setItem("marketflow_user", email);
    return { success: true, user: email };
  },

  logout() {
    localStorage.removeItem("marketflow_user");
  },

  getUser() {
    return localStorage.getItem("marketflow_user");
  }
};
