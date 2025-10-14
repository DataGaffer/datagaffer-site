// netlify/functions/stripe-webhook.js
exports.config = { rawBody: true };

const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

const ACTIVE_STATUSES = new Set(["active", "trialing", "past_due"]); // treat these as subscribed

function planFromPriceId(id) {
  if (!id) return null;
  if (id === process.env.STRIPE_PRICE_ID_MONTHLY) return "monthly";
  if (id === process.env.STRIPE_PRICE_ID_YEARLY) return "yearly";
  return null;
}

async function upsertProfile({ email, customerId, planCode, isSubscribed }) {
  if (!email) {
    console.warn("Missing email; cannot upsert profile");
    return;
  }
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
  if (error) console.error("Supabase upsert failed:", error);
  else console.log(`Upserted profile for ${email} (subscribed=${isSubscribed})`);
}

exports.handler = async (event) => {
  const sig = event.headers["stripe-signature"];
  let stripeEvent;
  try {
    stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("Signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log("Webhook:", stripeEvent.type);

  try {
    switch (stripeEvent.type) {
      case "checkout.session.completed": {
        const session = stripeEvent.data.object; // CheckoutSession
        const customerId = session.customer;
        // safest is to fetch the subscription to get price & status
        let priceId = null, status = null;
        if (session.subscription) {
          const sub = await stripe.subscriptions.retrieve(session.subscription);
          priceId = sub.items?.data?.[0]?.price?.id || null;
          status = sub.status;
        }
        const email =
          (session.customer_details?.email ||
            session.customer_email ||
            null);

        await upsertProfile({
          email,
          customerId,
          planCode: planFromPriceId(priceId),
          isSubscribed: ACTIVE_STATUSES.has(status || "active"), // sessions complete means they paid
        });
        break;
      }

      case "customer.subscription.created":
      case "customer.subscription.updated": {
        const sub = stripeEvent.data.object; // Subscription
        const customerId = sub.customer;
        const priceId = sub.items?.data?.[0]?.price?.id || null;
        const status = sub.status;
        const customer = await stripe.customers.retrieve(customerId);
        const email = customer?.email || null;

        await upsertProfile({
          email,
          customerId,
          planCode: planFromPriceId(priceId),
          isSubscribed: ACTIVE_STATUSES.has(status),
        });
        break;
      }

      case "customer.subscription.deleted": {
        const sub = stripeEvent.data.object; // Subscription
        const customerId = sub.customer;
        const customer = await stripe.customers.retrieve(customerId);
        const email = customer?.email || null;

        await upsertProfile({
          email,
          customerId,
          planCode: null,
          isSubscribed: false,
        });
        break;
      }

      default:
        // ignore other events
        break;
    }
  } catch (e) {
    console.error("Webhook handler error:", e);
    return { statusCode: 500, body: "handler error" };
  }

  return { statusCode: 200, body: "ok" };
};




