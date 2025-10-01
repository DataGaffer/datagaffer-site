const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);

exports.handler = async (event) => {
  try {
    const { plan } = JSON.parse(event.body); // ✅ read plan type from request body

    let priceId;
    let successUrl;

    if (plan === "20_old") {
      priceId = process.env.STRIPE_PRICE_ID; // old grandfathered $20 plan
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else if (plan === "20_new") {
      priceId = process.env.STRIPE_PRICE_ID_20_NEW; // new $20 plan (sim-only)
      successUrl = `${process.env.SITE_URL}/standard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else if (plan === "50") {
      priceId = process.env.STRIPE_PRICE_ID_50; // $50 plan
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else if (plan === "250") {
      priceId = process.env.STRIPE_PRICE_ID_250; // $250 plan
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else {
      throw new Error("Invalid plan selected");
    }

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      mode: "subscription",
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      subscription_data: {
        trial_period_days: 7, // ✅ 7-day free trial
      },
      success_url: successUrl,
      cancel_url: `${process.env.SITE_URL}/subscribe.html`,
    });

    return {
      statusCode: 200,
      body: JSON.stringify({ url: session.url }),
    };
  } catch (error) {
    console.error("❌ Stripe Checkout Error:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
};





