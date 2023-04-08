<?php

    function file_get_contents_curl($url, $retries=5){
        $ua = 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)';
        if (extension_loaded('curl') === true)
        {
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $url); // The URL to fetch. This can also be set when initializing a session with curl_init().
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, TRUE); // TRUE to return the transfer as a string of the return value of curl_exec() instead of outputting it out directly.
            curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5); // The number of seconds to wait while trying to connect.
            curl_setopt($ch, CURLOPT_USERAGENT, $ua); // The contents of the "User-Agent: " header to be used in a HTTP request.
            curl_setopt($ch, CURLOPT_FAILONERROR, TRUE); // To fail silently if the HTTP code returned is greater than or equal to 400.
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, TRUE); // To follow any "Location: " header that the server sends as part of the HTTP header.
            curl_setopt($ch, CURLOPT_AUTOREFERER, TRUE); // To automatically set the Referer: field in requests where it follows a Location: redirect.
            curl_setopt($ch, CURLOPT_TIMEOUT, 5); // The maximum number of seconds to allow cURL functions to execute.
            curl_setopt($ch, CURLOPT_MAXREDIRS, 5); // The maximum number of redirects
            $result = trim(curl_exec($ch));
            curl_close($ch);
        }
        else
        {
            $result = trim(file_get_contents($url));
        }
        if (empty($result) === true)
        {
            $result = false;
            if ($retries >= 1)
            {
                sleep(1);
                return file_get_contents_curl($url, --$retries);
            }
        }
        return $result;
    }

    function all_tweets($username, $get_dates=false){
        $page = file_get_contents_curl("https://mobile.twitter.com/$username");
        preg_match_all(
            '{<div class="tweet-text" data-id="(\d+)">\s*<div class="dir-ltr" dir="ltr">\s*(.+?)\s*</div>\s*</div>}',
            $page,
            $matches
        );
        #if (empty($matches[1])) return array();
        $ids   = array_values($matches[1]);
        $texts = array_values($matches[2]);
        unset($matches);
        $results = array();
        for ($i=1,$c=count($ids) ; $i<$c ; $i++ ){
            $results[] = array(
                'id'    => $ids[$i],
                'text'  => strip_tags($texts[$i]),
            );
        }

        if ($get_dates) {
            $dates = array();
            preg_match_all(
                '{<a name="tweet_(\d+)"[^>]+>([^>]+)</a>}',
                $page,
                $dates
            );
            $dds = array();
            if (!empty($dates[1])) for ($i=0,$c=count($dates[1]) ; $i<$c ; $i++ ) $dds[$dates[1][$i]] = $dates[2][$i];
            if ($dds) foreach($results as &$tweet){
                if (isset($dds[$tweet['id']])){
                    $tweet['date'] = $dds[$tweet['id']];
                }
            }
        }
        return $results;
    }

    if(isset($_GET['un'])){
        $u = $_GET['un'];
        $count  = $_GET['count'];

        $tweets = all_tweets($u, true);
        $tweets = array_slice($tweets, 0, $count);
        echo json_encode($tweets);

    }


?>
