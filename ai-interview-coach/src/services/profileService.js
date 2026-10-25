export function profileName(user) {
  return user?.full_name?.trim() || user?.email?.split("@")[0] || "Your account";
}

export function profileInitial(user) {
  return Array.from(profileName(user))[0].toLocaleUpperCase();
}
