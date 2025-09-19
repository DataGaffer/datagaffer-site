// netlify/functions/stripe-webhook.js
const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

// Supabase client (service role required here!)
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Netlify requires this to bypass body parsing
exports.handler = async (event, context) => {
  const sig = event.headers["stripe-signature"];
  let stripeEvent;

  try {
    // Stripe requires the raw body, NOT parsed JSON
    stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("⚠️ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  // ✅ Handle successful checkout
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;
    const email = session.customer_details?.email;

    if (email) {
      const { error } = await supabase
        .from("profiles")
        .update({ is_subscribed: true })
        .eq("email", email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`✅ Subscription activated for ${email}`);
    }
  }

  // ✅ Handle subscription canceled
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;
    const customer = await stripe.customers.retrieve(subscription.customer);

    if (customer?.email) {
      const { error } = await supabase
        .from("profiles")
        .update({ is_subscribed: false })
        .eq("email", customer.email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`✅ Subscription canceled for ${customer.email}`);
    }
  }

  return { statusCode: 200, body: "success" };
};

// 🚨 Tell Netlify not to parse JSON
exports.config = {
  bodyParser: false,
};


