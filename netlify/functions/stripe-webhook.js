// netlify/functions/stripe-webhook.js
exports.config = { rawBody: true };

const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Treat these statuses as "subscribed"
const ACTIVE_STATUSES = new Set(["active", "trialing", "past_due"]);

function planFromPriceId(id) {
  if (!id) return null;
  if (id === process.env.STRIPE_PRICE_ID_MONTHLY) return "monthly";
  if (id === process.env.STRIPE_PRICE_ID_YEARLY) return "yearly";
  return null;
}

async function upsertProfile({ email, customerId, planCode, isSubscribed, status }) {
  if (!email) {
    console.warn("⚠️ Missing email; cannot upsert profile");
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
        subscription_status: status || null, // optional: helps you track 'trialing' vs 'active'
      },
      { onConflict: "email" }
    );

  if (error) console.error("❌ Supabase upsert failed:", error);
  else console.log(`✅ Upserted profile for ${email} (${status || "unknown"})`);
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
    console.error("❌ Signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log("📩 Webhook received:", stripeEvent.type);

  try {
    switch (stripeEvent.type) {
      // ------------------------------
      // ✅ CHECKOUT COMPLETED
      // ------------------------------
      case "checkout.session.completed": {
        const session = stripeEvent.data.object;

        // 🛑 Skip unpaid trial checkouts
        if (session.payment_status !== "paid" && !session.subscription) {
          console.log("⏭️ Skipping unpaid trial checkout (awaiting subscription.created)");
          break;
        }

        let priceId = null;
        let status = null;
        let customerId = session.customer;

        if (session.subscription) {
          const sub = await stripe.subscriptions.retrieve(session.subscription);
          priceId = sub.items?.data?.[0]?.price?.id || null;
          status = sub.status;
          customerId = sub.customer;
        } else if (session.customer) {
          const subs = await stripe.subscriptions.list({
            customer: session.customer,
            limit: 1,
          });
          if (subs.data.length) {
            priceId = subs.data[0].items?.data?.[0]?.price?.id || null;
            status = subs.data[0].status;
            customerId = subs.data[0].customer;
          }
        }

        const email =
          session.customer_details?.email ||
          session.customer_email ||
          null;

        await upsertProfile({
          email,
          customerId,
          planCode: planFromPriceId(priceId),
          isSubscribed: ACTIVE_STATUSES.has(status || "active"),
          status,
        });

        break;
      }

      // ------------------------------
      // ✅ SUBSCRIPTION CREATED/UPDATED
      // ------------------------------
      case "customer.subscription.created":
      case "customer.subscription.updated": {
        const sub = stripeEvent.data.object;
        const customerId = sub.customer;
        const priceId = sub.items?.data?.[0]?.price?.id || null;
        const status = sub.status;
        const customer = await stripe.customers.retrieve(customerId);
        const email = customer?.email || null;

        console.log(`🔔 Subscription event (${status}) for ${email}`);

        await upsertProfile({
          email,
          customerId,
          planCode: planFromPriceId(priceId),
          isSubscribed: ACTIVE_STATUSES.has(status),
          status,
        });
        break;
      }

      // ------------------------------
      // 🚫 SUBSCRIPTION CANCELLED/EXPIRED
      // ------------------------------
      case "customer.subscription.deleted": {
        const sub = stripeEvent.data.object;
        const customerId = sub.customer;
        const customer = await stripe.customers.retrieve(customerId);
        const email = customer?.email || null;

        await upsertProfile({
          email,
          customerId,
          planCode: null,
          isSubscribed: false,
          status: "canceled",
        });

        console.log(`🛑 Subscription canceled for ${email}`);
        break;
      }

      default:
        console.log("ℹ️ Ignored event type:", stripeEvent.type);
        break;
    }
  } catch (e) {
    console.error("💥 Webhook handler error:", e);
    return { statusCode: 500, body: "handler error" };
  }

  return { statusCode: 200, body: "ok" };
};





