// netlify/functions/stripe-webhook.js
exports.config = {
  rawBody: true,
};

const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  console.log("⚡ Incoming webhook event");

  const sig = event.headers["stripe-signature"];
  let stripeEvent;

  try {
    stripeEvent = stripe.webhooks.constructEvent(
      event.body, // raw string
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("❌ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log("✅ Webhook verified:", stripeEvent.type);

  // 🔹 Handle checkout complete → activate subscription
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;
    const email = session.customer_details?.email;
    const customerId = session.customer;

    if (email && customerId) {
      const { error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: true,
          customer_id: customerId, // ✅ save customer ID
        })
        .eq("email", email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`✅ Subscription activated for ${email}, customer ${customerId}`);
    }
  }

  // 🔹 Handle subscription updates (renewal, plan change, etc.)
  if (stripeEvent.type === "customer.subscription.updated") {
    const subscription = stripeEvent.data.object;
    const customerId = subscription.customer;
    const status = subscription.status; // "active", "past_due", "canceled", etc.

    const customer = await stripe.customers.retrieve(customerId);
    const email = customer.email;

    if (email) {
      const { error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: status === "active",
          customer_id: customerId,
        })
        .eq("email", email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`🔄 Subscription updated for ${email}: ${status}`);
    }
  }

  // 🔹 Handle subscription cancellation
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;
    const customerId = subscription.customer;

    const customer = await stripe.customers.retrieve(customerId);
    const email = customer.email;

    if (email) {
      const { error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: false,
          customer_id: customerId, // ✅ keep ID for history
        })
        .eq("email", email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`✅ Subscription canceled for ${email}`);
    }
  }

  return { statusCode: 200, body: "success" };
};




