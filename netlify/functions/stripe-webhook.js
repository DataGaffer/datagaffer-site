// ✅ Netlify must pass raw body
export const config = { rawBody: true };

import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

// --- Stripe & Supabase clients ---
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

const ACTIVE_STATUSES = new Set(["active", "trialing", "past_due"]);

// --- Identify plan from price ID ---
function planFromPriceId(id) {
  if (!id) return null;
  if (id === process.env.STRIPE_PRICE_ID_MONTHLY) return "monthly";
  if (id === process.env.STRIPE_PRICE_ID_YEARLY) return "yearly";
  return null;
}

// --- Upsert profile in Supabase ---
async function upsertProfile({ email, customerId, planCode, isSubscribed }) {
  if (!email) return;
  email = email.toLowerCase();

  // 🧠 Fetch existing row for this email if it exists
  const { data: existing } = await supabase
    .from("profiles")
    .select("id, email, is_subscribed, plan, customer_id, trial_used")
    .eq("email", email)
    .maybeSingle();

  // --- 🧩 Merge with existing data ---
  const updatePayload = {
    email,
    customer_id: customerId ?? existing?.customer_id ?? null,
    plan: isSubscribed ? planCode : existing?.plan ?? null,
    is_subscribed: isSubscribed || existing?.is_subscribed || false,
  };

  // Preserve the auth-linked ID if one already exists
  if (existing?.id) updatePayload.id = existing.id;

  const { error } = await supabase
    .from("profiles")
    .upsert(updatePayload, { onConflict: "email" });

  if (error) console.error("❌ Supabase upsert failed:", error);
  else
    console.log(
      `✅ Upserted ${email} | subscribed=${updatePayload.is_subscribed} | plan=${updatePayload.plan}`
    );
}

// --- 🧩 NEW: Mark trial used ---
async function markTrialUsed(customerId) {
  const { error } = await supabase
    .from("profiles")
    .update({ trial_used: true })
    .eq("customer_id", customerId);

  if (error) console.error("❌ Error marking trial_used:", error);
  else console.log(`✅ Marked trial used for ${customerId}`);
}

// --- Main handler ---
export async function handler(event) {
  console.log("📩 Stripe webhook received");

  if (!event.body) {
    console.error("❌ No webhook body");
    return { statusCode: 400, body: "Webhook Error: No webhook payload was provided." };
  }

  const sig = event.headers["stripe-signature"];
  if (!sig) {
    console.error("❌ Missing Stripe signature");
    return { statusCode: 400, body: "Webhook Error: Missing Stripe signature" };
  }

  let stripeEvent;
  try {
    stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("❌ Signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log(`✅ Verified event: ${stripeEvent.type}`);

  try {
    switch (stripeEvent.type) {
      case "checkout.session.completed": {
        const session = stripeEvent.data.object;
        const email =
          session.customer_details?.email ||
          session.customer_email ||
          null;
        const customerId = session.customer;
        let planCode = null;
        let isSubscribed = false;

        if (session.subscription) {
          const sub = await stripe.subscriptions.retrieve(session.subscription);
          const priceId = sub.items?.data?.[0]?.price?.id || null;
          planCode = planFromPriceId(priceId);
          isSubscribed = ACTIVE_STATUSES.has(sub.status);

          // 🧩 NEW: If this subscription started with a trial, mark it now
          if (sub.trial_end && sub.trial_end > Math.floor(Date.now() / 1000)) {
            await markTrialUsed(customerId);
          }
        }

        await upsertProfile({ email, customerId, planCode, isSubscribed });
        break;
      }

      case "customer.subscription.created":
      case "customer.subscription.updated": {
        const sub = stripeEvent.data.object;
        const customer = await stripe.customers.retrieve(sub.customer);
        const email = customer?.email || null;
        const planCode = planFromPriceId(sub.items?.data?.[0]?.price?.id);
        const isSubscribed = ACTIVE_STATUSES.has(sub.status);

        // 🧩 NEW: Mark trial used once it ends or if it was created with a trial
        if (sub.trial_end && sub.trial_end < Math.floor(Date.now() / 1000)) {
          await markTrialUsed(sub.customer);
        }

        await upsertProfile({ email, customerId: sub.customer, planCode, isSubscribed });
        break;
      }

      case "customer.subscription.deleted": {
        const sub = stripeEvent.data.object;
        const customer = await stripe.customers.retrieve(sub.customer);
        const email = customer?.email || null;

        await upsertProfile({
          email,
          customerId: sub.customer,
          planCode: null,
          isSubscribed: false,
        });
        break;
      }

      default:
        console.log("ℹ️ Ignored event:", stripeEvent.type);
    }
  } catch (err) {
    console.error("💥 Handler error:", err);
    return { statusCode: 500, body: "Handler error" };
  }

  return { statusCode: 200, body: "ok" };
}







