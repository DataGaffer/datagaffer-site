// netlify/functions/stripe-webhook.js
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

const ACTIVE_STATUSES = new Set(["active", "trialing", "past_due"]);

function planFromPriceId(id) {
  if (!id) return null;
  if (id === process.env.STRIPE_PRICE_ID_MONTHLY) return "monthly";
  if (id === process.env.STRIPE_PRICE_ID_YEARLY) return "yearly";
  return null;
}

async function upsertProfile({ email, customerId, planCode, isSubscribed }) {
  if (!email) return;
  email = email.toLowerCase();
  const { error } = await supabase
    .from("profiles")
    .upsert(
      {
        email,
        customer_id: customerId ?? null,
        plan: isSubscribed ? planCode : null,
        is_subscribed: !!isSubscribed,
      },
      { onConflict: "email" }
    );
  if (error) console.error("❌ Supabase upsert failed:", error);
  else console.log(`✅ Upserted ${email} (subscribed=${isSubscribed})`);
}

export async function handler(event) {
  const sig = event.headers["stripe-signature"];
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

  console.log("📩 Webhook received:", stripeEvent.type);

  try {
    switch (stripeEvent.type) {
      case "checkout.session.completed": {
        const session = stripeEvent.data.object;
        const email = session.customer_details?.email || session.customer_email || null;
        const customerId = session.customer;
        let planCode = null;
        let isSubscribed = false;

        if (session.subscription) {
          const sub = await stripe.subscriptions.retrieve(session.subscription);
          const priceId = sub.items?.data?.[0]?.price?.id || null;
          planCode = planFromPriceId(priceId);
          isSubscribed = ACTIVE_STATUSES.has(sub.status);
        }

        await upsertProfile({ email, customerId, planCode, isSubscribed });
        break;
      }

      case "customer.subscription.updated":
      case "customer.subscription.created": {
        const sub = stripeEvent.data.object;
        const customer = await stripe.customers.retrieve(sub.customer);
        const email = customer?.email || null;
        const planCode = planFromPriceId(sub.items?.data?.[0]?.price?.id);
        const isSubscribed = ACTIVE_STATUSES.has(sub.status);
        await upsertProfile({ email, customerId: sub.customer, planCode, isSubscribed });
        break;
      }

      case "customer.subscription.deleted": {
        const sub = stripeEvent.data.object;
        const customer = await stripe.customers.retrieve(sub.customer);
        const email = customer?.email || null;
        await upsertProfile({ email, customerId: sub.customer, planCode: null, isSubscribed: false });
        break;
      }

      default:
        console.log("ℹ️ Ignored event:", stripeEvent.type);
    }
  } catch (err) {
    console.error("💥 Handler error:", err);
    return { statusCode: 500, body: "handler error" };
  }

  return { statusCode: 200, body: "ok" };
}





