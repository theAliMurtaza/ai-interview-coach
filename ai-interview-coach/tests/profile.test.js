import test from "node:test";
import assert from "node:assert/strict";
import { profileInitial, profileName } from "../src/services/profileService.js";

test("profile initial uses the name, with an email fallback for older accounts", () => {
  assert.equal(profileInitial({ full_name: "  ali Murtaza", email: "someone@example.com" }), "A");
  assert.equal(profileInitial({ full_name: "Élodie" }), "É");
  assert.equal(profileName({ full_name: " Ali " }), "Ali");
  assert.equal(profileInitial({ full_name: " ", email: "alex@example.com" }), "A");
});
