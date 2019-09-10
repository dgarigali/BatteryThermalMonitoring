package com.rmsf.batterythermalmonitoring;

import android.content.DialogInterface;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.support.v7.app.AlertDialog;
import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.TextView;

import com.android.volley.AuthFailureError;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.Response;
import com.android.volley.VolleyError;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.StringRequest;
import com.android.volley.toolbox.Volley;

import com.github.nkzawa.emitter.Emitter;
import com.github.nkzawa.socketio.client.IO;
import com.github.nkzawa.socketio.client.Socket;

import org.json.JSONException;
import org.json.JSONObject;

import java.net.URISyntaxException;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends AppCompatActivity {

    //Fields
    private Socket mSocket;
    private AlertDialog alertDialog;
    private String url = "http://00.00.00.00:3002";
    private RequestQueue queue;
    private Button button;

    //Constructor
    {
        try {
            mSocket = IO.socket(url);
        } catch (URISyntaxException e) {}
    }

    private Emitter.Listener onConnect = new Emitter.Listener() {
        @Override
        public void call(final Object... args) {
            MainActivity.this.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    mSocket.emit("new_client");
                }
            });
        }
    };

    private Emitter.Listener FanEvent = new Emitter.Listener() {
        @Override
        public void call(final Object... args) {
            MainActivity.this.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    String json_str = args[0].toString();
                    try {
                        JSONObject data = new JSONObject(json_str);
                        TextView tv = (TextView)findViewById(R.id.FanState);
                        tv.setText(data.getString("fan"));
                    } catch (JSONException e) {
                    }
                }
            });
        }
    };

    private Emitter.Listener ModeEvent = new Emitter.Listener() {
        @Override
        public void call(final Object... args) {
            MainActivity.this.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    String json_str = args[0].toString();
                    try {
                        JSONObject data = new JSONObject(json_str);
                        TextView tv = (TextView)findViewById(R.id.CurrentMode);
                        tv.setText(data.getString("mode"));
                    } catch (JSONException e) {
                    }
                }
            });
        }
    };

    private Emitter.Listener ThresholdEvent = new Emitter.Listener() {
        @Override
        public void call(final Object... args) {
            MainActivity.this.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    String json_str = args[0].toString();
                    try {
                        JSONObject data = new JSONObject(json_str);
                        TextView tv = (TextView)findViewById(R.id.Threshold);
                        tv.setText(String.valueOf(data.getInt("threshold")));
                    } catch (JSONException e) {
                        return;
                    }
                }
            });
        }
    };

    private Emitter.Listener SensorEvent = new Emitter.Listener() {
        @Override
        public void call(final Object... args) {
            MainActivity.this.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    String json_str = args[0].toString();
                    try {
                        JSONObject data = new JSONObject(json_str);
                        TextView tv1 = (TextView)findViewById(R.id.SensorTimestamp);
                        TextView tv2 = (TextView)findViewById(R.id.SensorTemperature);
                        tv1.setText(data.getString("timestamp"));
                        tv2.setText(String.valueOf(data.getInt("temp")));
                    } catch (JSONException e) {
                        return;
                    }
                }
            });
        }
    };

    private Emitter.Listener CamaraEvent = new Emitter.Listener() {
        @Override
        public void call(final Object... args) {
            MainActivity.this.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    String json_str = args[0].toString();
                    try {
                        JSONObject data = new JSONObject(json_str);
                        TextView tv1 = (TextView)findViewById(R.id.CamaraTimestamp);
                        TextView tv2 = (TextView)findViewById(R.id.MaxTemperature);
                        TextView tv3 = (TextView)findViewById(R.id.MinTemperature);
                        tv1.setText(data.getString("timestamp"));
                        float max_temp = (float) (data.getInt("temp_max")/10.0);
                        tv2.setText(String.valueOf(max_temp));
                        float min_temp = (float) (data.getInt("temp_min")/10.0);
                        tv3.setText(String.valueOf(min_temp));
                    } catch (JSONException e) {
                        return;
                    }
                }
            });
        }
    };

    private Emitter.Listener ImageEvent = new Emitter.Listener() {
        @Override
        public void call(final Object... args) {
            MainActivity.this.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    byte[] byteArray = (byte []) args[0];
                    Bitmap bmp = BitmapFactory.decodeByteArray(byteArray, 0, byteArray.length);
                    ImageView image = (ImageView) findViewById(R.id.image);
                    image.setImageBitmap(Bitmap.createScaledBitmap(bmp, image.getWidth(), image.getHeight(), false));
                }
            });
        }
    };

    private Emitter.Listener DownlinkEvent = new Emitter.Listener() {
        @Override
        public void call(final Object... args) {
            MainActivity.this.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    String json_str = args[0].toString();
                    try {
                        JSONObject data_json = new JSONObject(json_str);
                        AlertDialog alertDialog = new AlertDialog.Builder(MainActivity.this).create();
                        alertDialog.setTitle("Alert");
                        alertDialog.setMessage(data_json.getString("msg"));
                        alertDialog.show();
                    } catch (JSONException e) {
                        return;
                    }
                }
            });
        }
    };

    private void updateSeekBar(boolean first_call) {
        SeekBar seekBar = findViewById(R.id.seekBar);
        int val = (seekBar.getProgress() * (seekBar.getWidth() - 2 * seekBar.getThumbOffset())) / seekBar.getMax();
        TextView textView = (TextView)findViewById(R.id.seekBarText);
        textView.setText("" + seekBar.getProgress());
        if(first_call) {
            textView.setX(-250);
        } else {
            textView.setX(seekBar.getX() + val + 15 + seekBar.getThumbOffset() / 2);
        }
        textView.setY(seekBar.getY() + 5);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        queue = Volley.newRequestQueue(this);

        //Subscribe to SocketIO events
        mSocket.on("connect", onConnect);
        mSocket.on("fan", FanEvent);
        mSocket.on("mode", ModeEvent);
        mSocket.on("threshold", ThresholdEvent);
        mSocket.on("env_temp", SensorEvent);
        mSocket.on("camara", CamaraEvent);
        mSocket.on("image", ImageEvent);
        mSocket.on("downlink", DownlinkEvent);
        mSocket.connect();

        //Set layout
        setContentView(R.layout.activity_main);

        //Prepare seekBar
        SeekBar seekBar = findViewById(R.id.seekBar);
        updateSeekBar(true);
        seekBar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
           @Override
           public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
               updateSeekBar(false);
           }
           @Override
           public void onStartTrackingTouch(SeekBar seekBar) {
           }
           @Override
           public void onStopTrackingTouch(SeekBar seekBar) {
           }
       });

        //Prepare button
        button = (Button) findViewById(R.id.button);
        button.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {

                //Get current values
                TextView tv = (TextView)findViewById(R.id.FanState);
                String current_fan = tv.getText().toString();
                tv = (TextView)findViewById(R.id.CurrentMode);
                String current_mode = tv.getText().toString();
                tv = (TextView)findViewById(R.id.Threshold);
                int current_threshold;
                if (tv.getText().toString().matches("")) {
                    current_threshold = 0;
                } else {
                    current_threshold = Integer.parseInt(tv.getText().toString());
                }

                //Get wanted values
                Spinner mySpinner = (Spinner) findViewById(R.id.spinnerFan);
                String fan = mySpinner.getSelectedItem().toString();
                mySpinner = (Spinner) findViewById(R.id.spinnerMode);
                String mode = mySpinner.getSelectedItem().toString();
                SeekBar seekBar2 = findViewById(R.id.seekBar);
                int threshold = seekBar2.getProgress();

                if (!current_fan.equals(fan) || !current_mode.equals(mode) || current_threshold != threshold) {

                    try {

                        final JSONObject json_data = new JSONObject("{\"threshold\": \"" + threshold + "\", \"fan\": \"" + fan + "\", \"mode\": \"" + mode + "\"}");
                        Map<String, String> jsonParams = new HashMap<String, String>();
                        jsonParams.put("data", json_data.toString());

                        JsonObjectRequest myRequest  = new JsonObjectRequest(Request.Method.POST, url + "/request", new JSONObject(jsonParams),
                                new Response.Listener<JSONObject>() {
                                    @Override
                                    public void onResponse(JSONObject data_json) {
                                        try {
                                            if (data_json.getBoolean("success")) {
                                                AlertDialog alertDialog = new AlertDialog.Builder(MainActivity.this).create();
                                                alertDialog.setTitle("Alert");
                                                alertDialog.setMessage("Downlink was requested!");
                                                alertDialog.show();
                                            } else {
                                                AlertDialog alertDialog = new AlertDialog.Builder(MainActivity.this).create();
                                                alertDialog.setTitle("Alert");
                                                alertDialog.setMessage(data_json.getString("msg"));
                                                alertDialog.show();
                                            }
                                        } catch (JSONException e) {
                                            return;
                                        }
                                    }
                                },
                                new Response.ErrorListener() {
                                    @Override
                                    public void onErrorResponse(VolleyError error) {
                                        AlertDialog alertDialog = new AlertDialog.Builder(MainActivity.this).create();
                                        alertDialog.setTitle("Alert");
                                        alertDialog.setMessage("No Internet connection or server is down!");
                                        alertDialog.show();
                                    }
                                }) {
                            @Override
                            public Map<String, String> getHeaders() throws AuthFailureError {
                                HashMap<String, String> headers = new HashMap<String, String>();
                                headers.put("Content-Type", "application/json; charset=utf-8");
                                return headers;
                            }
                        };
                        queue.add(myRequest);
                    } catch (JSONException e) {
                        e.printStackTrace();
                    }
                } else {
                    alertDialog = new AlertDialog.Builder(MainActivity.this).create();
                    alertDialog.setTitle("Alert");
                    alertDialog.setMessage("Setup parameters are equal than current parameters!");
                    alertDialog.show();
                }
            }
        });
    }
}
