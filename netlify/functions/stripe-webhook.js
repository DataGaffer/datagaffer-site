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
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error("❌ Webhook signature verification failed:", err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  console.log("✅ Webhook verified:", stripeEvent.type);

  // ------------------------------
  // Checkout completed → activate subscription + save plan
  // ------------------------------
  if (stripeEvent.type === "checkout.session.completed") {
    const session = stripeEvent.data.object;
    const email = session.customer_details?.email?.toLowerCase();
    const customerId = session.customer;

    // ✅ fetch line items explicitly
    const lineItems = await stripe.checkout.sessions.listLineItems(session.id, {
      limit: 1,
    });
    const priceId = lineItems.data[0]?.price?.id;

    let planCode = null;
    if (priceId === process.env.STRIPE_PRICE_ID) {
      planCode = "20_old";
    } else if (priceId === process.env.STRIPE_PRICE_ID_20_NEW) {
      planCode = "20_new";
    } else if (priceId === process.env.STRIPE_PRICE_ID_50) {
      planCode = "50";
    } else if (priceId === process.env.STRIPE_PRICE_ID_250) {
      planCode = "250";
    }

    console.log("Checkout completed:", { email, customerId, planCode });

    if (email && customerId && planCode) {
      const { error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: true,
          customer_id: customerId,
          plan: planCode,
        })
        .eq("email", email);

      if (error) {
        console.error("❌ Error updating Supabase:", error);
        return { statusCode: 500, body: "Supabase update failed" };
      }

      console.log(`✅ Subscription activated for ${email}, plan ${planCode}`);
    }
  }

  // ------------------------------
  // Subscription canceled → deactivate
  // ------------------------------
  if (stripeEvent.type === "customer.subscription.deleted") {
    const subscription = stripeEvent.data.object;
    const customerId = subscription.customer;

    const customer = await stripe.customers.retrieve(customerId);
    const email = customer.email?.toLowerCase();

    console.log("Subscription canceled for:", { email, customerId });

    if (email) {
      const { error } = await supabase
        .from("profiles")
        .update({
          is_subscribed: false,
          customer_id: null,
          plan: null,
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




