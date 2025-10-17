export const config = {
  rawBody: true,
};

import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function handler(event) {
  // Log what Netlify is actually sending
  console.log("🧩 typeof event.body:", typeof event.body);
  console.log("🧩 event.body length:", event.body?.length || 0);
  console.log("🧩 First 200 chars of body:", event.body?.slice(0, 200) || "");
  console.log("🧩 Stripe signature header:", event.headers["stripe-signature"]);
  console.log("🧩 STRIPE_WEBHOOK_SECRET exists:", !!process.env.STRIPE_WEBHOOK_SECRET);

  if (!event.body) {
    console.error("❌ No body found");
    return { statusCode: 400, body: "Webhook Error: No webhook payload was provided." };
  }

  const sig = event.headers["stripe-signature"];
  if (!sig) {
    console.error("❌ Missing Stripe signature header");
    return { statusCode: 400, body: "Webhook Error: Missing Stripe signature" };
  }

  try {
    const stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
    console.log("✅ Webhook verified:", stripeEvent.type);
  } catch (err) {
    console.error("❌ Verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  return { statusCode: 200, body: "ok" };
}





