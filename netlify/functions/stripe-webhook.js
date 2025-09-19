// netlify/functions/stripe-webhook.js
exports.config = {
  rawBody: true, // ✅ ensure Netlify sends raw body to Stripe
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

  // ------------------------------
  // Checkout completed → activate subscription
  // ------------------------------
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;
    const email = session.customer_details?.email?.toLowerCase(); // force lowercase
    const customerId = session.customer;

    console.log("Checkout completed:", { email, customerId });

    if (email && customerId) {
      // Debug: confirm row exists before update
      const { data: profileCheck } = await supabase
        .from("profiles")
        .select("id, email, is_subscribed, customer_id")
        .eq("email", email);

      console.log("🔎 Matching profile rows before update:", profileCheck);

      const { error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: true,
          customer_id: customerId,
        })
        .eq("email", email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`✅ Subscription activated for ${email}, customer ${customerId}`);
    }
  }

  // ------------------------------
  // Subscription canceled → deactivate
  // ------------------------------
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;
    const customerId = subscription.customer;

    // Retrieve customer email
    const customer = await stripe.customers.retrieve(customerId);
    const email = customer.email?.toLowerCase();

    console.log("Subscription canceled for:", { email, customerId });

    if (email) {
      const { error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: false,
          customer_id: null, // clear Stripe customer ID
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




