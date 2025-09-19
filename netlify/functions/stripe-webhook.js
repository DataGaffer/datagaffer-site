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
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("❌ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log("✅ Webhook verified:", stripeEvent.type);

  // Handle successful checkout
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;
    const email = session.customer_details?.email;
    const customerId = session.customer;

    console.log("Checkout completed:", { email, customerId });

    if (email && customerId) {
      const { data, error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: true,
          customer_id: customerId,
        })
        .eq("email", email)
        .select();

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log("✅ Updated profile:", data);
    } else {
      console.error("❌ Missing email or customerId in session");
    }
  }

  // Handle cancellation
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;
    const customerId = subscription.customer;

    const customer = await stripe.customers.retrieve(customerId);
    const email = customer.email;

    console.log("Subscription canceled:", { email, customerId });

    if (email) {
      const { data, error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: false,
          customer_id: null,
        })
        .eq("email", email)
        .select();

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log("✅ Canceled profile:", data);
    }
  }

  return { statusCode: 200, body: "success" };
};




